import json, subprocess, sys
from pathlib import Path
import pytest
from skillsgap.demand import parse_brightermonday_listing, parse_district_advert
from skillsgap.schema import estimate_posted_date, FIELDS
from skillsgap.supply import classify_field, classify_level, parse_graduation_pdf
from skillsgap.quality import report
from skillsgap.http import PoliteClient, RobotsDisallowed
from skillsgap.config import load_config

FX = Path(__file__).parent / "fixtures"
TS = "2026-10-21T14:00:00+00:00"


def test_bm_parser_dedupes_and_flags_missing_employer():
    recs, fails = parse_brightermonday_listing((FX / "bm_listing.html").read_text(), "https://x.test/jobs", TS)
    assert [r["title"] for r in recs] == ["Operations Manager", "Stock Controller", "Marketing Officer"]
    assert recs[0]["employer"] == "Cook Bright Initiative" and recs[0]["location"] == "Kampala"
    assert recs[1]["function_raw"] == "Supply Chain & Procurement"
    assert recs[1]["posted_date_est"] == "2026-10-07"
    assert any(f["reason"] == "employer_not_found" for f in fails)
    assert all(r["record_id"] and r["raw_hash"] and r["retrieved_at"] for r in recs)


def test_district_parser_rows_and_deadline():
    recs, fails = parse_district_advert((FX / "district_advert.html").read_text(), "https://d.test/n/1", TS)
    assert len(recs) == 2 and recs[0]["deadline"] == "30th September 2026"
    assert recs[1]["vacancies"] == "6" and any(f["reason"] == "row_without_title" for f in fails)


def test_posted_date_estimates():
    assert estimate_posted_date("Today", TS) == "2026-10-21"
    assert estimate_posted_date("Yesterday", TS) == "2026-10-20"
    assert estimate_posted_date("1 week ago", TS) == "2026-10-14"
    assert estimate_posted_date("garbage", TS) == ""


def test_graduation_pdf_counts_and_stores_no_names(tmp_path):
    sys.path.insert(0, str(Path(__file__).parent))
    from make_pdf_fixture import build
    p = tmp_path / "g.pdf"; build(str(p))
    meta = {"name": "TEST", "url": "https://t.test/g.pdf", "institution": "Test U", "ceremony": "1st"}
    recs, fails = parse_graduation_pdf(p.read_bytes(), meta, TS)
    got = {r["programme"]: r["graduate_count"] for r in recs}
    assert got["Bachelor of Science in Computer Science"] == 5 and got["Bachelor of Laws"] == 3
    assert any("Diploma in Business Studies" in f["reason"] for f in fails)
    blob = json.dumps(recs)
    assert "Testname" not in blob and "Surname" not in blob


def test_classifiers():
    assert classify_level("Master of Business Administration") == "Masters"
    assert classify_level("Postgraduate Diploma in Finance") == "Postgraduate diploma"
    assert classify_field("Bachelor of Science in Computer Science") == "STEM"
    assert classify_field("Bachelor of Laws") == "NON_STEM"
    assert classify_field("Bachelor of Medicine and Bachelor of Surgery") == "REVIEW_HEALTH"
    assert classify_field("Master of Information Technology Management") == "STEM"


def test_quality_report_provenance():
    recs, fails = parse_brightermonday_listing((FX / "bm_listing.html").read_text(), "https://x.test/jobs", TS)
    rep = report(recs, fails)
    assert rep["provenance_incomplete"] == 0 and rep["by_source"]["brightermonday"] == 3


class FakeResp:
    def __init__(self, code, body=b"ok", headers=None):
        self.status_code, self.content, self.headers = code, body, headers or {}
        self.text = body.decode()
    def raise_for_status(self):
        import requests
        if self.status_code >= 400: raise requests.HTTPError(str(self.status_code))

class FakeSession:
    def __init__(self, seq): self.seq, self.calls, self.headers = list(seq), [], {}
    def get(self, url, timeout=None):
        self.calls.append(url)
        if url.endswith("/robots.txt"): return FakeResp(200, b"User-agent: *\nDisallow: /private\n")
        return self.seq.pop(0)


def _client(tmp_path, seq, sleeps):
    cfg = load_config(); cfg["http"]["cache_dir"] = str(tmp_path / "c")
    return PoliteClient(cfg, "TestUA", tmp_path, session=FakeSession(seq), sleep=sleeps.append)


def test_retry_backoff_then_success_and_cache(tmp_path):
    sleeps = []
    c = _client(tmp_path, [FakeResp(503), FakeResp(200, b"hello")], sleeps)
    body, meta = c.get("https://h.test/a")
    assert body == b"hello" and c.stats["retries"] == 1 and any(s >= 2 for s in sleeps)
    body2, meta2 = c.get("https://h.test/a")
    assert meta2["from_cache"] and c.stats["cache_hits"] == 1 and c.stats["requests"] == 2


def test_robots_disallow_blocks(tmp_path):
    c = _client(tmp_path, [], [])
    with pytest.raises(RobotsDisallowed):
        c.get("https://h.test/private/x")


def test_rate_limit_spaces_requests(tmp_path):
    sleeps = []
    c = _client(tmp_path, [FakeResp(200, b"1"), FakeResp(200, b"2")], sleeps)
    c.get("https://h.test/1"); c.get("https://h.test/2")
    assert any(s > 0 for s in sleeps)


def test_end_to_end_run_with_fake_client(tmp_path):
    """Whole pipeline (extract->transform->load) against fixtures served by a fake client."""
    import copy
    from skillsgap import pipeline
    cfg = copy.deepcopy(load_config())
    cfg["sources"]["brightermonday"]["listing_url"] = "https://bm.test/jobs"
    cfg["sources"]["district_adverts"]["urls"] = ["https://d.test/n/1"]
    cfg["sources"]["graduation_lists"]["lists"] = []
    pages = {"https://bm.test/jobs": (FX / "bm_listing.html").read_bytes(),
             "https://d.test/n/1": (FX / "district_advert.html").read_bytes()}

    class FakeClient:
        ua = "TestUA"; stats = {"requests": 0}
        def get(self, url):
            if url not in pages: return b"<html></html>", {"from_cache": False}
            return pages[url], {"from_cache": False}

    recs, fails, rep = pipeline.run(cfg, tmp_path / "out", client=FakeClient())
    assert rep["by_source"] == {"brightermonday": 3, "district_adverts": 2}
    assert rep["provenance_incomplete"] == 0
    for f in ("dataset.csv", "dataset.json", "quality_report.json", "compliance_run_log.csv", "run_manifest.json"):
        assert (tmp_path / "out" / f).exists()
    # re-run is idempotent: identical record ids
    recs2, _, _ = pipeline.run(cfg, tmp_path / "out2", client=FakeClient())
    assert sorted(r["record_id"] for r in recs) == sorted(r["record_id"] for r in recs2)


def test_district_text_rows_parsed_from_real_advert_layout():
    recs, fails = parse_district_advert((FX / "district_advert_text.html").read_text(), "https://d.test/n/61", TS)
    assert [r["title"] for r in recs] == ["District Education Officer", "Education Assistant II",
                                          "Principal Internal Auditor", "Senior Accountant",
                                          "Assistant Law Enforcement Officer"]
    assert recs[1]["vacancies"] == "6" and recs[3]["ref_no"] == "LYDSC/4/4/2026"
    assert recs[0]["deadline"] == "30th September 2026" and not fails


def test_highest_serial_beats_matched_rows_and_heading_cleanup():
    from skillsgap.supply import count_programmes, clean_heading
    lines = ["BACHELOR OF LAWS", "1 A B", "2 C D", "garbled line", "4 E F", "9 G H",
             "2025 Graduation Ceremony", "DIPLOMA IN BUSINESS STUDIES t", "1 X Y"]
    b, orphan = count_programmes(lines)
    # the stray "2025 ..." line is matched as a row but must NOT become the count (last valid serial = 9)
    assert b[0] == ("BACHELOR OF LAWS", 5, 9) and b[1][0] == "DIPLOMA IN BUSINESS STUDIES"
    assert clean_heading("BACHELOR OF SCIENCE IN COMPUTER SCIENCE .'qt('") == "BACHELOR OF SCIENCE IN COMPUTER SCIENCE"


def test_bm_real_card_structure():
    recs, fails = parse_brightermonday_listing((FX / "bm_card_real.html").read_text(), "https://x.test/jobs", TS)
    r = recs[0]
    assert r["title"] == "Sales & Marketing Executive" and r["employer"] == "The Dove's Nest Hotel"
    assert r["location"] == "Rest of Uganda (Gulu)" and r["employment_type"] == "Full Time"
    assert r["salary_text"] == "USh 500,000 - 1,000,000" and r["function_raw"] == "Marketing & Communications"
    assert r["record_url"].endswith("sales-marketing-executive-7wezne") and not fails


def test_bm_age_found_outside_card_and_not_mixed_between_jobs():
    recs, fails = parse_brightermonday_listing((FX / "bm_age_sibling.html").read_text(), "https://x.test/jobs", TS)
    got = {r["title"]: (r["employer"], r["location"], r["posted_text"], r["posted_date_est"]) for r in recs}
    assert got["Job A"] == ("Employer A", "Kampala", "2 weeks ago", "2026-10-07")
    assert got["Job B"][2] == "5 days ago"
    assert got["Job C"][2] == ""          # no age shown for this job: must stay empty, not borrow a neighbour's


def test_serial_jump_and_confidence():
    from skillsgap.supply import count_programmes, count_confidence
    lines = ["MASTER OF PUBLIC HEALTH"] + [f"{n} A B" for n in (1, 2, 3, 40, 41)] + ["99999 x"]
    b, _ = count_programmes(lines)
    assert b[0][2] == 41                       # jump of 37 (a lost page) accepted, stray number ignored
    assert count_confidence(41, 41) == "high" and count_confidence(74, 18) == "low" and count_confidence(30, 22) == "medium"
