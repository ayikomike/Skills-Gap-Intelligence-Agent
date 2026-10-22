"""Build data/sample/ from the captured seed rows using the SAME schema, id and quality code as the
live pipeline. Records are tagged retrieval_method='manual_fetch_tool_capture' so nobody mistakes them
for pipeline-collected rows. Run:  PYTHONPATH=src python scripts/build_seed_dataset.py"""
import json
from pathlib import Path
from skillsgap.demand import _host_label
from skillsgap.quality import report
from skillsgap.schema import estimate_posted_date, make_record, write_csv, write_json
from skillsgap.supply import classify_field, classify_level

ROOT = Path(__file__).resolve().parents[1]
M = "manual_fetch_tool_capture"
d = json.loads((ROOT / "data/seed/captured_demand.json").read_text())
s = json.loads((ROOT / "data/seed/captured_supply.json").read_text())
recs = []
bm = d["brightermonday"]
for title, emp, loc, posted, func in bm["rows"]:
    recs.append(make_record("demand", "brightermonday", bm["source_url"], d["retrieved_at"], M,
        id_parts=[title, emp], raw_for_hash=f"{title}|{emp}|{loc}|{posted}|{func}",
        title=title, employer=emp, location=loc, posted_text=posted,
        posted_date_est=estimate_posted_date(posted, d["retrieved_at"]), function_raw=func))
da = d["district_adverts"]
for dept, title, ref, scale, vac in da["rows"]:
    recs.append(make_record("demand", "district_adverts", da["source_url"], d["retrieved_at"], M,
        id_parts=[da["source_url"], ref, title], raw_for_hash=f"{dept}|{title}|{ref}|{scale}|{vac}",
        record_url=da["source_url"], title=title, employer=da["employer"], department=dept,
        ref_no=ref, salary_scale=scale, vacancies=vac, deadline=da["deadline"], function_raw=dept))
for lst in s["lists"]:
    for prog, n, basis in lst["rows"]:
        recs.append(make_record("supply", lst["name"], lst["url"], s["retrieved_at"], M,
            id_parts=[lst["url"], prog], raw_for_hash=f"{prog}|{n}", record_url=lst["url"],
            institution=lst["institution"], ceremony=lst["ceremony"], award_level=classify_level(prog),
            programme=prog, graduate_count=n, count_basis=basis, field_group_provisional=classify_field(prog)))
out = ROOT / "data/sample"; out.mkdir(parents=True, exist_ok=True)
write_csv(recs, out / "TeamName_Week3_Dataset.csv"); write_json(recs, out / "dataset_sample.json")
rep = report(recs, [{"url": s["identified_not_parsed"][0]["url"], "reason": s["identified_not_parsed"][0]["reason"]}])
(out / "quality_report_seed.json").write_text(json.dumps(rep, indent=2))
print(json.dumps(rep, indent=2))
