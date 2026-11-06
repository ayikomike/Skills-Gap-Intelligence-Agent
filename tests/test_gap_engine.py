"""Tests for the Week 6 gap engine. Run: python -m pytest tests/test_gap_engine.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from skillsgap.gap import engine as E  # noqa: E402

RULES = pd.DataFrame([
    {"rule_id": "A", "side": "supply", "pattern": "education", "category_id": "DOM-05",
     "priority": 2, "certainty": "certain"},
    {"rule_id": "B", "side": "supply", "pattern": "governance", "category_id": "DOM-07",
     "priority": 2, "certainty": "certain"},
    {"rule_id": "C", "side": "supply", "pattern": "management", "category_id": "DOM-06",
     "priority": 1, "certainty": "certain"},
])


def test_priority_and_fractional_split():
    m = E.map_record("PGD in Education Management / Urban Governance", "supply", RULES, "combined")
    assert m["categories"] == ["DOM-05", "DOM-07"]          # priority-1 'management' dropped
    assert m["weights"] == [0.5, 0.5] and sum(m["weights"]) == 1
    assert m["certainty"] == "uncertain"                     # combined count split is uncertain


def test_unmapped():
    m = E.map_record("Bachelor of Theology", "supply", RULES)
    assert m["categories"] == [E.UNMAPPED] and m["certainty"] == "unmapped"


def _cfg():
    return {"scope": {"exclude_locations": ["Outside Uganda"], "intermediary_employers": []}}


def _records():
    base = dict(source="s", source_url="u", record_url="u", retrieved_at="t", pipeline_version="0.1.0",
                ceremony="c", award_level="", count_basis="exact", field_group_provisional="NON_STEM",
                vacancies=np.nan)
    rows = [
        dict(base, record_id="d1", record_type="demand", title="Accountant", employer="X",
             location="Kampala", raw_hash="h1", institution=np.nan, programme=np.nan, graduate_count=np.nan),
        dict(base, record_id="d2", record_type="demand", title="Accountant", employer="X",
             location="Kampala", raw_hash="h2", institution=np.nan, programme=np.nan, graduate_count=np.nan),
        dict(base, record_id="d3", record_type="demand", title="Accountant", employer="Y",
             location="Outside Uganda", raw_hash="h3", institution=np.nan, programme=np.nan, graduate_count=np.nan),
        dict(base, record_id="s1", record_type="supply", title=np.nan, employer=np.nan, location=np.nan,
             raw_hash="h4", institution="U", programme="BCom", graduate_count=10),
        dict(base, record_id="s2", record_type="supply", title=np.nan, employer=np.nan, location=np.nan,
             raw_hash="h5", institution="U", programme="BEd", graduate_count=np.nan),
    ]
    return pd.DataFrame(rows)


def test_duplicates_scope_and_missing():
    p = E.prepare_records(_records(), _cfg()).set_index("record_id")
    assert p.at["d2", "status_detail"] == "duplicate" and p.at["d2", "duplicate_of"] == "d1"
    assert p.at["d3", "status"] == "out_of_scope"
    assert p.at["s2", "status_detail"] == "missing_graduate_count"
    assert p.at["d1", "status"] == "in_scope" and p.at["s1", "status"] == "in_scope"


def test_shares_sum_to_one_and_gap_sums_to_zero():
    j = pd.DataFrame([
        {"record_id": "d1", "side": "demand", "status": "in_scope", "category_id": "A", "weighted_units": 1},
        {"record_id": "d2", "side": "demand", "status": "in_scope", "category_id": "B", "weighted_units": 0.5},
        {"record_id": "d2", "side": "demand", "status": "in_scope", "category_id": "A", "weighted_units": 0.5},
        {"record_id": "s1", "side": "supply", "status": "in_scope", "category_id": "B", "weighted_units": 30},
        {"record_id": "s2", "side": "supply", "status": "in_scope", "category_id": E.UNMAPPED, "weighted_units": 99},
    ])
    s = E.shares(j, ["A", "B", "C"])
    assert abs(s.demand_share.sum() - 1) < 1e-9 and abs(s.supply_share.sum() - 1) < 1e-9
    assert abs(s.gap_pp.sum()) < 1e-9                       # unmapped rows are outside the denominator
    assert s.at["A", "gap_pp"] == 75.0 and s.at["B", "gap_pp"] == -75.0
    assert np.isnan(s.at["A", "ratio_index"])                # undefined when supply share is 0


def test_full_run_reproducible(tmp_path):
    cfg = E.load_config()
    cfg["output_dir"] = str(tmp_path)
    p = tmp_path / "cfg.yaml"
    import yaml
    p.write_text(yaml.safe_dump(cfg))
    r1 = E.run(p)
    r2 = E.run(p)
    pd.testing.assert_frame_equal(r1["results"], r2["results"])
    res = r1["results"]
    assert abs(res.demand_share.sum() - 1) < 1e-9 and abs(res.supply_share.sum() - 1) < 1e-9
    j = r1["joined"]
    assert j.groupby("record_id").weight.sum().round(9).eq(1).all()   # every record counts once
    assert j[["source_url", "retrieved_at", "raw_hash", "input_sha256"]].notna().all().all()
