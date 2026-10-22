"""Polite HTTP client: honest UA, robots.txt, per-host rate limit, disk cache, retry/backoff, logging."""
import hashlib
import json
import logging
import random
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import requests

log = logging.getLogger("skillsgap.http")


class RobotsDisallowed(Exception):
    pass


class PoliteClient:
    def __init__(self, cfg, user_agent, root, session=None, sleep=time.sleep, offline=False):
        h = cfg["http"]
        self.min_delay = float(h["min_delay_seconds"])
        self.timeout = h["timeout_seconds"]
        self.max_retries = int(h["max_retries"])
        self.backoff = float(h["backoff_base_seconds"])
        self.respect_robots = bool(h["respect_robots"])
        self.ttl = float(h["cache_ttl_hours"]) * 3600
        self.cache_dir = Path(root) / h["cache_dir"]
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ua = user_agent
        self.offline = offline
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._sleep = sleep
        self._last = {}
        self._robots = {}
        self.stats = {"requests": 0, "cache_hits": 0, "retries": 0, "errors": 0, "robots_blocked": 0}

    # -- robots.txt -------------------------------------------------------
    def allowed(self, url):
        if not self.respect_robots:
            return True
        u = urlparse(url)
        base = f"{u.scheme}://{u.netloc}"
        rp = self._robots.get(base)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.session.get(base + "/robots.txt", timeout=self.timeout)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
                log.info("robots.txt %s -> HTTP %s", base, r.status_code)
            except requests.RequestException as e:
                log.warning("robots.txt unreachable for %s (%s); treating as no rules", base, e)
                rp.parse([])
            self._robots[base] = rp
        return rp.can_fetch(self.ua, url)

    # -- cache ------------------------------------------------------------
    def _cache_path(self, url):
        return self.cache_dir / (hashlib.sha256(url.encode()).hexdigest()[:32] + ".json")

    def _read_cache(self, url):
        p = self._cache_path(url)
        if p.exists() and time.time() - p.stat().st_mtime < self.ttl:
            d = json.loads(p.read_text(encoding="utf-8"))
            return d
        return None

    def _write_cache(self, url, content_b64, status, ctype):
        self._cache_path(url).write_text(
            json.dumps({"url": url, "status": status, "content_type": ctype,
                        "fetched_at": time.time(), "body_b64": content_b64}), encoding="utf-8")

    # -- fetch ------------------------------------------------------------
    def get(self, url):
        """Return (bytes, meta). meta has status, content_type, from_cache, fetched_at."""
        import base64
        cached = self._read_cache(url)
        if cached:
            self.stats["cache_hits"] += 1
            log.info("CACHE %s", url)
            return base64.b64decode(cached["body_b64"]), {
                "status": cached["status"], "content_type": cached["content_type"],
                "from_cache": True, "fetched_at": cached["fetched_at"]}
        if self.offline:
            raise RuntimeError(f"offline mode and no fresh cache for {url}")
        if not self.allowed(url):
            self.stats["robots_blocked"] += 1
            log.warning("ROBOTS DISALLOW %s", url)
            raise RobotsDisallowed(url)
        host = urlparse(url).netloc
        for attempt in range(self.max_retries + 1):
            wait = self.min_delay - (time.time() - self._last.get(host, 0))
            if wait > 0:
                self._sleep(wait)
            self._last[host] = time.time()
            self.stats["requests"] += 1
            try:
                r = self.session.get(url, timeout=self.timeout)
                log.info("GET %s -> %s (attempt %d)", url, r.status_code, attempt + 1)
                if r.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"HTTP {r.status_code}")
                r.raise_for_status()
                ctype = r.headers.get("Content-Type", "")
                self._write_cache(url, base64.b64encode(r.content).decode(), r.status_code, ctype)
                return r.content, {"status": r.status_code, "content_type": ctype,
                                   "from_cache": False, "fetched_at": time.time()}
            except requests.RequestException as e:
                self.stats["retries"] += 1
                if attempt >= self.max_retries:
                    self.stats["errors"] += 1
                    log.error("FAILED %s after %d attempts: %s", url, attempt + 1, e)
                    raise
                delay = self.backoff * (2 ** attempt) + random.uniform(0, 0.5)
                log.warning("retry %s in %.1fs (%s)", url, delay, e)
                self._sleep(delay)
