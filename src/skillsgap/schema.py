"""Unified record schema (v0.2, revised after Week 3 labelling) and writers.

Every record carries provenance: source, source_url, record_url, retrieved_at,
retrieval_method, pipeline_version, raw_hash, plus a stable record_id.
No personal data is stored: graduation lists are reduced to programme-level counts.
"""
import csv
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from . import __version__

PROVENANCE = ["record_id", "record_type", "source", "source_url", "record_url",
              "retrieved_at", "retrieval_method", "pipeline_version", "raw_hash"]
DEMAND = ["title", "employer", "location", "posted_text", "posted_date_est", "function_raw",
          "department", "ref_no", "salary_scale", "vacancies", "deadline", "employment_type", "salary_text",
          "description_raw"]
SUPPLY = ["institution", "ceremony", "award_level", "programme", "graduate_count",
          "count_basis", "rows_matched", "count_confidence", "field_group_provisional"]
FIELDS = PROVENANCE + DEMAND + SUPPLY


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha(*parts):
    return hashlib.sha256("|".join(str(p or "").strip().lower() for p in parts).encode()).hexdigest()


def make_record(record_type, source, source_url, retrieved_at, method, id_parts, raw_for_hash, **fields):
    rec = {k: "" for k in FIELDS}
    rec.update(fields)
    rec.update({
        "record_type": record_type, "source": source, "source_url": source_url,
        "retrieved_at": retrieved_at, "retrieval_method": method,
        "pipeline_version": __version__,
        "record_id": f"{source}:{sha(*id_parts)[:16]}",
        "raw_hash": sha(raw_for_hash),
    })
    return rec


_REL = re.compile(r"(\d+)\s+(day|week|month|year)s?\s+ago", re.I)


def estimate_posted_date(text, retrieved_iso):
    """Convert 'Today', 'Yesterday', '4 days ago' to an ESTIMATED date (precision is coarse)."""
    if not text:
        return ""
    base = datetime.fromisoformat(retrieved_iso).date()
    t = text.strip().lower()
    if t == "today":
        return base.isoformat()
    if t == "yesterday":
        return (base - timedelta(days=1)).isoformat()
    m = _REL.search(t)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        days = {"day": 1, "week": 7, "month": 30, "year": 365}[unit] * n
        return (base - timedelta(days=days)).isoformat()
    return ""


def write_csv(records, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)


def write_json(records, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False)
