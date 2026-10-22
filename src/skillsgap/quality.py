"""Data-quality report: counts by source, missingness, duplicates, parse failures, provenance completeness."""
from collections import Counter

from .schema import DEMAND, PROVENANCE, SUPPLY


def report(records, failures, client_stats=None):
    by_source = Counter(r["source"] for r in records)
    out = {"total_records": len(records), "by_source": dict(by_source),
           "by_type": dict(Counter(r["record_type"] for r in records))}
    miss = {}
    for rtype, fields in (("demand", DEMAND), ("supply", SUPPLY)):
        subset = [r for r in records if r["record_type"] == rtype]
        if not subset:
            continue
        miss[rtype] = {f: round(100 * sum(1 for r in subset if str(r.get(f, "")).strip() == "") / len(subset), 1)
                       for f in fields}
    out["missing_pct"] = miss
    ids = Counter(r["record_id"] for r in records)
    out["duplicate_record_ids"] = sum(1 for v in ids.values() if v > 1)
    demand = [r for r in records if r["record_type"] == "demand"]
    keys = Counter((r["title"].lower(), r["employer"].lower()) for r in demand)
    out["demand_duplicate_title_employer"] = sum(v - 1 for v in keys.values() if v > 1)
    prov_missing = [r["record_id"] for r in records if any(str(r.get(f, "")).strip() == "" for f in
                    ("record_id", "source", "source_url", "retrieved_at", "retrieval_method", "raw_hash"))]
    out["provenance_incomplete"] = len(prov_missing)
    out["no_stable_record_url"] = sum(1 for r in records if not r.get("record_url"))
    out["supply_count_confidence"] = dict(Counter(r.get("count_confidence", "") for r in records
                                                  if r["record_type"] == "supply"))
    out["parse_failures"] = len(failures)
    out["parse_failure_detail"] = failures[:20]
    if client_stats:
        out["http"] = client_stats
    return out
