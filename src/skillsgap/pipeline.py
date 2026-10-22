"""ETL entry point.   python -m skillsgap.pipeline --out out/            (fresh run)
                      python -m skillsgap.pipeline --out out/ --offline   (re-run from cache only)
Extract (polite fetch + cache) -> Transform (pure parsers) -> Load (CSV/JSON + quality report + manifest).
A source runs only if enabled in config/sources.yaml AND has an approval string recorded there."""
import argparse
import csv
import hashlib
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .config import load_config, user_agent
from .demand import parse_brightermonday_listing, parse_district_advert
from .http import PoliteClient, RobotsDisallowed
from .quality import report
from .schema import now_iso, write_csv, write_json
from .supply import parse_graduation_pdf

log = logging.getLogger("skillsgap.pipeline")


def run(cfg, out_dir, only=None, offline=False, client=None):
    out = Path(out_dir)
    (out / "logs").mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(out / "logs" / "pipeline.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.getLogger().addHandler(fh)
    logging.getLogger().setLevel(logging.INFO)
    client = client or PoliteClient(cfg, user_agent(cfg), cfg["_root"], offline=offline)
    lim = cfg["limits"]
    started = now_iso()
    records, failures, compliance = [], [], []

    def gate(name, scfg):
        if only and name not in only:
            return False
        if not scfg.get("enabled") or not scfg.get("approval"):
            log.warning("SKIP %s: not enabled or no approval recorded", name)
            return False
        return True

    for name, scfg in cfg["sources"].items():
        if not gate(name, scfg):
            continue
        n_before = len(records)
        try:
            if name == "brightermonday":
                for page in range(1, lim["max_pages_per_source"] + 1):
                    url = scfg["listing_url"] + ("" if page == 1 else f"?page={page}")
                    body, meta = client.get(url)
                    ts = now_iso()
                    recs, fails = parse_brightermonday_listing(body.decode("utf-8", "replace"), url, ts,
                                                              "cache_replay" if meta["from_cache"] else "http_get")
                    records += recs; failures += fails
                    if not recs or len(records) - n_before >= lim["max_records_per_source"]:
                        break
            elif name == "district_adverts":
                for url in scfg["urls"]:
                    body, meta = client.get(url)
                    recs, fails = parse_district_advert(body.decode("utf-8", "replace"), url, now_iso(),
                                                       method="cache_replay" if meta["from_cache"] else "http_get")
                    records += recs; failures += fails
            elif name == "graduation_lists":
                for item in scfg["lists"]:
                    if item.get("enabled") is False:
                        log.info("SKIP list %s (disabled in config)", item["name"])
                        continue
                    body, meta = client.get(item["url"])
                    recs, fails = parse_graduation_pdf(body, item, now_iso(),
                                                       "cache_replay" if meta["from_cache"] else "http_get")
                    records += recs; failures += fails
        except RobotsDisallowed as e:
            failures.append({"url": str(e), "reason": "robots_disallowed"})
        except Exception as e:  # keep going: one failing source must not stop the run
            log.exception("source %s failed", name)
            failures.append({"url": name, "reason": f"collection_error: {e}"})
        compliance.append({"source": name, "approval": scfg.get("approval"), "tos_note": scfg.get("tos_note", ""),
                           "records_collected": len(records) - n_before, "rate_limit_s": cfg["http"]["min_delay_seconds"],
                           "user_agent": client.ua})

    seen_ids, unique = set(), []
    for r in records:  # listings shift between pages, so the same posting can appear twice
        if r["record_id"] in seen_ids:
            continue
        seen_ids.add(r["record_id"]); unique.append(r)
    dup_dropped = len(records) - len(unique)
    records[:] = unique
    write_csv(records, out / "dataset.csv")
    write_json(records, out / "dataset.json")
    rep = report(records, failures, client.stats)
    rep["duplicates_dropped_before_write"] = dup_dropped
    (out / "quality_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    with open(out / "compliance_run_log.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(compliance[0].keys()) if compliance else ["source"])
        w.writeheader(); w.writerows(compliance)
    manifest = {"pipeline_version": __version__, "started_at": started, "finished_at": now_iso(),
                "offline": offline, "config_sha256": hashlib.sha256(json.dumps(
                    {k: v for k, v in cfg.items() if k != "_root"}, sort_keys=True).encode()).hexdigest(),
                "records": len(records)}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return records, failures, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description="Skills-Gap ETL pipeline v1")
    ap.add_argument("--config"); ap.add_argument("--out", default="out")
    ap.add_argument("--sources", help="comma-separated subset of source names")
    ap.add_argument("--offline", action="store_true", help="use cache only; make no network requests")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load_config(a.config)
    only = set(a.sources.split(",")) if a.sources else None
    recs, fails, rep = run(cfg, a.out, only, a.offline)
    print(json.dumps({"records": len(recs), "by_source": rep["by_source"], "parse_failures": len(fails)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
