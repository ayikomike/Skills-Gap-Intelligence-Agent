"""Week 6 supply-demand gap-analysis engine.

Run from the repository root:
    python src/skillsgap/gap/engine.py                 # primary run + all checks
    python src/skillsgap/gap/engine.py --config other.yaml

Metric (see docs/week6_methodology.md):
    D_c = demand units mapped to category c / all mapped in-scope demand units
    S_c = graduates mapped to category c   / all mapped graduates
    G_c = 100 * (D_c - S_c)   percentage points  (primary gap)
    R_c = D_c / S_c           relative index     (secondary; undefined when S_c = 0)

Categories are Week 4 taxonomy domains (DOM-01 ... DOM-15). Records are mapped to
categories by the versioned rules in config/week6/mapping_rules.csv; a record that maps
to several categories is split equally (fractional counting), so every record counts once.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CFG = REPO_ROOT / "config" / "week6" / "gap_engine.yaml"
UNMAPPED = "UNMAPPED"


# --------------------------------------------------------------------------- loading
def _p(rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else REPO_ROOT / p


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def norm(s) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def load_config(path=None) -> dict:
    return yaml.safe_load(open(path or DEFAULT_CFG, encoding="utf-8"))


def load_taxonomy(cfg: dict) -> tuple[pd.DataFrame, str, str]:
    """Return (taxonomy, sha256, where-it-came-from). Reads the xlsx, else the Week 4 zip."""
    xlsx = _p(cfg["inputs"]["taxonomy_xlsx"])
    if xlsx.exists():
        data, origin = xlsx.read_bytes(), str(xlsx.relative_to(REPO_ROOT))
    else:
        zp = _p(cfg["inputs"]["taxonomy_zip"])
        if not zp.exists():
            sys.exit(f"Taxonomy not found: {xlsx} or {zp}")
        with zipfile.ZipFile(zp) as z:
            member = next(n for n in z.namelist()
                          if n.replace("\\", "/").endswith(cfg["inputs"]["taxonomy_member"]))
            data = z.read(member)
        origin = f"{zp.name}::{cfg['inputs']['taxonomy_member']}"
    tx = pd.read_excel(io.BytesIO(data))
    return tx, sha256_bytes(data), origin


def load_inputs(cfg: dict) -> dict:
    rec_path = _p(cfg["inputs"]["records"])
    guard = _p(cfg["inputs"]["heldout_guard"])
    if rec_path.resolve() == guard.resolve():
        sys.exit("Refusing to analyse the Week 8 held-out file before Week 8.")
    records = pd.read_csv(rec_path)
    tx, tx_sha, tx_origin = load_taxonomy(cfg)
    cats = pd.read_csv(_p(cfg["inputs"]["categories"]))
    labels = tx[tx.concept_type == "domain"][["concept_id", "preferred_label"]]
    cats = cats.merge(labels, left_on="category_id", right_on="concept_id", how="left")
    if cats.preferred_label.isna().any():
        bad = cats[cats.preferred_label.isna()].category_id.tolist()
        sys.exit(f"categories.csv has IDs that are not taxonomy domains: {bad}")
    cats = cats.rename(columns={"preferred_label": "category_label"}).drop(columns="concept_id")
    rules = pd.read_csv(_p(cfg["inputs"]["mapping_rules"]))
    unknown = set(rules.category_id) - set(cats.category_id)
    if unknown:
        sys.exit(f"mapping_rules.csv targets unknown categories: {unknown}")
    c2c = pd.read_csv(_p(cfg["inputs"]["concept_to_category"]))
    ext = pd.read_csv(_p(cfg["inputs"]["week5_extractions"]))
    lab_path = _p(cfg["inputs"]["week5_labels"])
    labels_df = pd.read_csv(lab_path) if lab_path.exists() else pd.DataFrame()
    versions = {
        "engine_version": cfg["engine_version"],
        "records_file": cfg["inputs"]["records"],
        "records_sha256": sha256_file(rec_path),
        "records_version": cfg["inputs"]["records_version"],
        "records_pipeline_version": ",".join(sorted(records.pipeline_version.astype(str).unique())),
        "taxonomy_source": tx_origin,
        "taxonomy_sha256": tx_sha,
        "taxonomy_version": ",".join(sorted(tx.version.astype(str).unique())),
        "taxonomy_review_status": ",".join(sorted(tx.review_status.astype(str).unique())),
        "extraction_file": cfg["inputs"]["week5_extractions"],
        "extraction_sha256": sha256_file(_p(cfg["inputs"]["week5_extractions"])),
        "extraction_method_version": ",".join(sorted(ext.method_version.astype(str).unique())),
        "mapping_rules_sha256": sha256_file(_p(cfg["inputs"]["mapping_rules"])),
        "categories_sha256": sha256_file(_p(cfg["inputs"]["categories"])),
        "concept_to_category_sha256": sha256_file(_p(cfg["inputs"]["concept_to_category"])),
        "config_sha256": sha256_file(Path(cfg["_path"])),
    }
    return dict(records=records, tx=tx, cats=cats, rules=rules, c2c=c2c, ext=ext,
                labels=labels_df, versions=versions)


# --------------------------------------------------------------------------- prepare
def prepare_records(records: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Scope, missing-data and duplicate decisions. One row per input record."""
    df = records.copy()
    df["side"] = df.record_type.str.lower()
    df["text_mapped"] = np.where(df.side == "demand", df.title, df.programme)
    df["units"] = np.where(df.side == "demand", 1.0,
                           pd.to_numeric(df.graduate_count, errors="coerce"))
    df["status"] = "in_scope"
    df["status_detail"] = ""

    missing_text = df.text_mapped.isna() | (df.text_mapped.astype(str).str.strip() == "")
    df.loc[missing_text, ["status", "status_detail"]] = ["excluded", "missing_title_or_programme"]
    bad_units = (df.side == "supply") & (df.units.isna() | (df.units <= 0))
    df.loc[bad_units & (df.status == "in_scope"), ["status", "status_detail"]] = \
        ["excluded", "missing_graduate_count"]

    out_loc = (df.side == "demand") & df.location.isin(cfg["scope"]["exclude_locations"])
    df.loc[out_loc & (df.status == "in_scope"), ["status", "status_detail"]] = \
        ["out_of_scope", "job_located_outside_uganda"]

    df["is_intermediary"] = (df.side == "demand") & df.employer.isin(
        cfg["scope"]["intermediary_employers"])

    # duplicates: same title + employer (demand), same institution + ceremony + programme (supply)
    df["dedup_key"] = np.where(
        df.side == "demand",
        "D|" + df.title.map(norm) + "|" + df.employer.map(norm),
        "S|" + df.institution.map(norm) + "|" + df.ceremony.map(norm) + "|" + df.programme.map(norm))
    df["duplicate_of"] = ""
    first = {}
    for i, r in df.iterrows():
        if r.status == "excluded":
            continue
        for key in (r.dedup_key, f"H|{r.raw_hash}"):
            if key in first:
                df.at[i, "duplicate_of"] = first[key]
                df.at[i, "status"], df.at[i, "status_detail"] = "excluded", "duplicate"
                break
        else:
            first[r.dedup_key] = r.record_id
            first[f"H|{r.raw_hash}"] = r.record_id
    return df


# --------------------------------------------------------------------------- mapping
def map_record(text: str, side: str, rules: pd.DataFrame, count_basis: str = "") -> dict:
    """Apply mapping rules to one title. Returns categories, weights, rules fired, certainty."""
    hits = []
    for r in rules[rules.side == side].itertuples():
        if re.search(r.pattern, str(text), flags=re.IGNORECASE):
            hits.append(r)
    if not hits:
        return {"categories": [UNMAPPED], "weights": [1.0], "rules": [], "certainty": "unmapped"}
    top = max(h.priority for h in hits)
    kept = [h for h in hits if h.priority == top]
    cats = sorted({h.category_id for h in kept})
    certain_cats = {h.category_id for h in kept if h.certainty == "certain"}
    split = len(cats) > 1
    certainty = "certain" if (not split and cats[0] in certain_cats) else "uncertain"
    if split and str(count_basis) == "combined":
        certainty = "uncertain"
    return {"categories": cats, "weights": [1.0 / len(cats)] * len(cats),
            "rules": sorted({h.rule_id for h in kept}), "certainty": certainty}


def week5_evidence(ext: pd.DataFrame, labels: pd.DataFrame, c2c: pd.DataFrame) -> pd.DataFrame:
    """Week 5 non-domain extractions per record, minus those reviewed as FP/wrong_mapping."""
    e = ext[ext.predicted_type.isin(["occupation", "skill"])].copy()
    if not labels.empty and "review_status" in labels:
        bad = labels[labels.review_status.isin(["FP", "wrong_mapping"])]
        bad_keys = set(zip(bad.posting_id, bad.extracted_span, bad.taxonomy_id))
        e = e[[k not in bad_keys for k in zip(e.posting_id, e.extracted_span, e.taxonomy_id)]]
    e = e.merge(c2c[["concept_id", "category_id"]], left_on="taxonomy_id",
                right_on="concept_id", how="left")
    return (e.groupby("posting_id")
             .agg(week5_concepts=("taxonomy_id", lambda s: ";".join(sorted(set(s)))),
                  week5_categories=("category_id",
                                    lambda s: ";".join(sorted(set(s.dropna())))))
             .reset_index())


def build_joined(prep: pd.DataFrame, inp: dict, mapping: str = "rules") -> pd.DataFrame:
    """Long table: one row per record x category, with weights and full lineage.
    mapping='rules' (primary) or 'week5_first' (use Week 5 extraction where it exists)."""
    ev = week5_evidence(inp["ext"], inp["labels"], inp["c2c"])
    prep = prep.merge(ev, left_on="record_id", right_on="posting_id", how="left").drop(
        columns="posting_id")
    cats = inp["cats"].set_index("category_id")
    v = inp["versions"]
    rows = []
    for r in prep.itertuples():
        m = map_record(r.text_mapped, r.side, inp["rules"], getattr(r, "count_basis", ""))
        basis = "rule"
        w5 = r.week5_categories if isinstance(r.week5_categories, str) and r.week5_categories else ""
        if mapping == "week5_first" and w5:
            cs = w5.split(";")
            m = {"categories": cs, "weights": [1 / len(cs)] * len(cs),
                 "rules": [], "certainty": "uncertain" if len(cs) > 1 else "certain"}
            basis = "week5_extraction"
        agrees = ""
        if w5:
            agrees = "Y" if set(w5.split(";")) & set(m["categories"]) else "N"
        for c, w in zip(m["categories"], m["weights"]):
            rows.append({
                "record_id": r.record_id, "side": r.side, "source": r.source,
                "organisation": r.employer if r.side == "demand" else r.institution,
                "text_mapped": r.text_mapped, "location": r.location,
                "status": r.status, "status_detail": r.status_detail,
                "duplicate_of": r.duplicate_of, "is_intermediary": bool(r.is_intermediary),
                "units": r.units, "category_id": c,
                "category_label": cats.category_label.get(c, "Not mapped to a taxonomy domain"),
                "stem_group": cats.stem_group.get(c, ""),
                "weight": round(w, 6), "weighted_units": (r.units or 0) * w,
                "mapping_basis": basis if c != UNMAPPED else "none",
                "rules_fired": ";".join(m["rules"]), "mapping_certainty": m["certainty"],
                "split_n": len(m["categories"]),
                "count_basis": r.count_basis if r.side == "supply" else "",
                "field_group_provisional": r.field_group_provisional if r.side == "supply" else "",
                "award_level": r.award_level if r.side == "supply" else "",
                "week5_concepts": r.week5_concepts if isinstance(r.week5_concepts, str) else "",
                "week5_categories": w5, "week5_agrees_with_rules": agrees,
                "source_url": r.source_url, "record_url": r.record_url,
                "retrieved_at": r.retrieved_at, "pipeline_version": r.pipeline_version,
                "raw_hash": r.raw_hash, "input_sha256": v["records_sha256"],
                "taxonomy_version": v["taxonomy_version"], "engine_version": v["engine_version"],
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- metric
def analysable(j: pd.DataFrame) -> pd.DataFrame:
    """Rows that enter the shares: in scope, not duplicate, mapped to a category."""
    return j[(j.status == "in_scope") & (j.category_id != UNMAPPED)]


def shares(j: pd.DataFrame, cat_ids: list[str]) -> pd.DataFrame:
    a = analysable(j)
    d = a[a.side == "demand"].groupby("category_id").weighted_units.sum()
    s = a[a.side == "supply"].groupby("category_id").weighted_units.sum()
    out = pd.DataFrame(index=pd.Index(cat_ids, name="category_id"))
    out["demand_units"] = d.reindex(cat_ids).fillna(0.0)
    out["supply_graduates"] = s.reindex(cat_ids).fillna(0.0)
    dt, st = out.demand_units.sum(), out.supply_graduates.sum()
    out["demand_share"] = out.demand_units / dt if dt else np.nan
    out["supply_share"] = out.supply_graduates / st if st else np.nan
    out["gap_pp"] = 100 * (out.demand_share - out.supply_share)
    out["ratio_index"] = np.where(out.supply_share > 0, out.demand_share / out.supply_share, np.nan)
    return out


def bootstrap(j: pd.DataFrame, cat_ids, reps: int, seed: int, interval: float) -> pd.DataFrame:
    """Resample demand records and supply programme rows independently, with replacement."""
    a = analysable(j)
    rng = np.random.default_rng(seed)
    mats = {}
    for side in ("demand", "supply"):
        piv = (a[a.side == side].pivot_table(index="record_id", columns="category_id",
                                             values="weighted_units", aggfunc="sum")
               .reindex(columns=cat_ids).fillna(0.0))
        mats[side] = piv.to_numpy()
    gaps = np.empty((reps, len(cat_ids)))
    for b in range(reps):
        sh = []
        for side in ("demand", "supply"):
            m = mats[side]
            pick = m[rng.integers(0, len(m), len(m))].sum(axis=0)
            sh.append(pick / pick.sum())
        gaps[b] = 100 * (sh[0] - sh[1])
    lo, hi = (1 - interval) / 2, 1 - (1 - interval) / 2
    return pd.DataFrame({"ci_low_pp": np.quantile(gaps, lo, axis=0),
                         "ci_high_pp": np.quantile(gaps, hi, axis=0)},
                        index=pd.Index(cat_ids, name="category_id"))


def category_results(j: pd.DataFrame, inp: dict, cfg: dict) -> pd.DataFrame:
    cats = inp["cats"]
    ids = cats.category_id.tolist()
    res = shares(j, ids)
    a = analysable(j)
    for side, col in (("demand", "demand_records"), ("supply", "supply_programmes")):
        res[col] = a[a.side == side].groupby("category_id").record_id.nunique().reindex(ids).fillna(0).astype(int)
        unc = a[(a.side == side) & (a.mapping_certainty != "certain")].groupby(
            "category_id").weighted_units.sum().reindex(ids).fillna(0)
        tot = res["demand_units" if side == "demand" else "supply_graduates"]
        res[f"{side}_uncertain_share"] = np.where(tot > 0, unc / tot.replace(0, np.nan), np.nan)
        res[f"{side}_record_ids"] = a[a.side == side].groupby("category_id").record_id.apply(
            lambda s: ";".join(sorted(set(s)))).reindex(ids).fillna("")
    bs = bootstrap(j, ids, cfg["bootstrap"]["reps"], cfg["bootstrap"]["seed"],
                   cfg["bootstrap"]["interval"])
    res = res.join(bs)
    res["sign_robust"] = np.where(
        (res.demand_units == 0) & (res.supply_graduates == 0), "no evidence",
        np.where((res.ci_low_pp > 0) | (res.ci_high_pp < 0), "yes", "no"))
    sup = cfg["support"]
    res["support"] = np.select(
        [(res.demand_units == 0) & (res.supply_graduates == 0),
         (res.demand_units < sup["min_demand_units"]) | (res.supply_graduates < sup["min_supply_graduates"])],
        ["NO EVIDENCE", "LOW SUPPORT"], "OK")
    res = cats.set_index("category_id").join(res)
    return res.reset_index()


# --------------------------------------------------------------------------- checks
def coverage(j: pd.DataFrame) -> pd.DataFrame:
    rec = j.drop_duplicates("record_id")
    rows = []
    for side in ("demand", "supply"):
        r = rec[rec.side == side]
        units = r.units.fillna(0)
        mapped = set(analysable(j)[analysable(j).side == side].record_id)
        in_scope = r[r.status == "in_scope"]
        rows.append({
            "side": side, "records_in_file": len(r),
            "excluded_missing": int((r.status_detail.str.startswith("missing")).sum()),
            "excluded_duplicate": int((r.status_detail == "duplicate").sum()),
            "out_of_scope": int((r.status == "out_of_scope").sum()),
            "in_scope_records": len(in_scope),
            "unmapped_in_scope": int(len(in_scope) - len(mapped)),
            "analysed_records": len(mapped),
            "analysed_units": float(analysable(j)[analysable(j).side == side].weighted_units.sum()),
            "in_scope_units": float(in_scope.units.fillna(0).sum()),
            "uncertain_records": int(rec[(rec.side == side) & rec.record_id.isin(mapped)
                                         & (rec.mapping_certainty != "certain")].shape[0]),
            "split_records": int(rec[(rec.side == side) & rec.record_id.isin(mapped)
                                     & (rec.split_n > 1)].shape[0]),
        })
    return pd.DataFrame(rows)


def ratio_x5(stem: float, hum: float) -> float:
    return 5 * stem / hum if hum else np.nan


def stem_ratio(j: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """NDPIV 441(ii) comparison: graduates STEM : humanities, written as x : 5."""
    rec = j[(j.status == "in_scope")].drop_duplicates("record_id")
    sup = rec[rec.side == "supply"]
    cur = cfg["ndpiv_441ii"]["current_stem_to_humanities"]
    tgt = cfg["ndpiv_441ii"]["target_stem_to_humanities"]
    rows = []

    def add(name, df, health, note):
        g = df.groupby("field_group_provisional").units.sum()
        stem, hum, hl = g.get("STEM", 0.0), g.get("NON_STEM", 0.0), g.get("REVIEW_HEALTH", 0.0)
        if health == "stem":
            stem += hl
        elif health == "humanities":
            hum += hl
        rows.append({"variant": name, "stem_graduates": stem, "humanities_graduates": hum,
                     "health_graduates_excluded": hl if health == "exclude" else 0.0,
                     "stem_per_5_humanities": ratio_x5(stem, hum),
                     "ndpiv_current_per_5": 5 * cur[0] / cur[1],
                     "ndpiv_target_per_5": 5 * tgt[0] / tgt[1],
                     "comparable_to_ndpiv": "NO - two-institution convenience sample",
                     "note": note})

    add("Primary: supply, health excluded", sup, "exclude",
        "Week 3 field_group_provisional; NON_STEM used as humanities (MAP-004 caveat)")
    add("Health counted as STEM", sup, "stem", "Sensitivity for MAP-006")
    add("Health counted as humanities", sup, "humanities", "Sensitivity for MAP-006")
    exact = sup[sup.count_basis.isin(["exact", "numbered_rows_counted"])]
    add("Exact counts only (drops approx/combined)", exact, "exclude",
        "Removes every IUIU row, which are all approximate")
    for inst, df in sup.groupby("organisation"):
        add(f"Institution: {inst}", df, "exclude", "Single institution")
    # demand-side analogue, by category stem_group (not the NDPIV measure)
    d = analysable(j)
    d = d[d.side == "demand"].groupby("stem_group").weighted_units.sum()
    stem, hum = d.get("STEM", 0.0), d.get("NON_STEM", 0.0)
    rows.append({"variant": "Demand analogue: postings in STEM vs non-STEM categories",
                 "stem_graduates": stem, "humanities_graduates": hum,
                 "health_graduates_excluded": d.get("REVIEW_HEALTH", 0.0),
                 "stem_per_5_humanities": ratio_x5(stem, hum),
                 "ndpiv_current_per_5": 5 * cur[0] / cur[1], "ndpiv_target_per_5": 5 * tgt[0] / tgt[1],
                 "comparable_to_ndpiv": "NO - counts postings, not graduates",
                 "note": "Units are postings; shown only to contrast demand mix with supply mix"})
    return pd.DataFrame(rows)


def sensitivity(prep: pd.DataFrame, inp: dict, cfg: dict) -> pd.DataFrame:
    """Recompute the gap under alternative, documented choices."""
    ids = inp["cats"].category_id.tolist()
    base = build_joined(prep, inp)
    scen = {"S0 primary": base}

    j = base.copy()
    unc = set(j[j.mapping_certainty != "certain"].record_id)
    j.loc[j.record_id.isin(unc), "status"] = "excluded"
    scen["S1 certain mappings only"] = j

    p2 = prep.copy()
    p2.loc[p2.status_detail == "job_located_outside_uganda", ["status", "status_detail"]] = ["in_scope", ""]
    scen["S2 include jobs outside Uganda"] = build_joined(p2, inp)

    j = base.copy()
    j.loc[j.is_intermediary, "status"] = "excluded"
    scen["S3 exclude intermediary employers"] = j

    j = base.copy()
    j.loc[(j.side == "supply") & ~j.count_basis.isin(["exact", "numbered_rows_counted"]), "status"] = "excluded"
    scen["S4 exact supply counts only"] = j

    scen["S5 Week 5 extraction mapping first"] = build_joined(prep, inp, mapping="week5_first")

    j = base.copy()
    big = j[j.side == "supply"].groupby("record_id").units.first().nlargest(2).index
    j.loc[j.record_id.isin(big), "status"] = "excluded"
    scen["S6 drop two largest programmes"] = j

    out = []
    s0 = shares(base, ids)
    for name, jj in scen.items():
        s = shares(jj, ids)
        a = analysable(jj)
        for c in ids:
            out.append({"scenario": name, "category_id": c,
                        "demand_units_total": a[a.side == "demand"].weighted_units.sum(),
                        "supply_graduates_total": a[a.side == "supply"].weighted_units.sum(),
                        "demand_share": s.at[c, "demand_share"], "supply_share": s.at[c, "supply_share"],
                        "gap_pp": s.at[c, "gap_pp"],
                        "change_vs_primary_pp": s.at[c, "gap_pp"] - s0.at[c, "gap_pp"]})
    return pd.DataFrame(out)


def week5_agreement(j: pd.DataFrame) -> dict:
    rec = j.drop_duplicates("record_id")
    w = rec[rec.week5_agrees_with_rules != ""]
    return {"records_with_week5_evidence": int(len(w)),
            "agree": int((w.week5_agrees_with_rules == "Y").sum()),
            "disagree_record_ids": w[w.week5_agrees_with_rules == "N"].record_id.tolist()}


# --------------------------------------------------------------------------- main
def run(cfg_path=None) -> dict:
    cfg = load_config(cfg_path)
    cfg["_path"] = str(cfg_path or DEFAULT_CFG)
    inp = load_inputs(cfg)
    prep = prepare_records(inp["records"], cfg)
    joined = build_joined(prep, inp)
    results = category_results(joined, inp, cfg)
    cov = coverage(joined)
    ratio = stem_ratio(joined, cfg)
    sens = sensitivity(prep, inp, cfg)
    agree = week5_agreement(joined)

    out = _p(cfg["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    joined.to_csv(out / "joined_records.csv", index=False)
    results.to_csv(out / "category_results.csv", index=False)
    cov.to_csv(out / "coverage.csv", index=False)
    ratio.to_csv(out / "stem_ratio.csv", index=False)
    sens.to_csv(out / "sensitivity.csv", index=False)
    rec = joined.drop_duplicates(["record_id", "category_id"])
    rec[(rec.category_id == UNMAPPED) | (rec.mapping_certainty != "certain") |
        (rec.status != "in_scope")].to_csv(out / "unmatched_uncertain_excluded.csv", index=False)

    manifest = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                **inp["versions"], "week5_agreement": agree,
                "outputs": {p.name: sha256_file(p) for p in sorted(out.glob("*.csv"))}}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2))

    a = analysable(joined)
    top = results[results.support != "NO EVIDENCE"].sort_values("gap_pp")
    print(f"Engine {cfg['engine_version']} | records {inp['versions']['records_sha256'][:12]} "
          f"| taxonomy v{inp['versions']['taxonomy_version']}")
    print(cov.to_string(index=False))
    print(f"\nDenominators: {a[a.side == 'demand'].weighted_units.sum():.0f} postings, "
          f"{a[a.side == 'supply'].weighted_units.sum():.0f} graduates")
    cols = ["category_id", "category_label", "demand_share", "supply_share", "gap_pp",
            "ci_low_pp", "ci_high_pp", "support"]
    print(top[cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\n" + ratio[["variant", "stem_graduates", "humanities_graduates",
                        "stem_per_5_humanities"]].to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(f"\nWeek 5 agreement: {agree['agree']}/{agree['records_with_week5_evidence']}")
    print(f"Outputs -> {out}")
    return {"joined": joined, "results": results, "coverage": cov, "ratio": ratio,
            "sensitivity": sens, "manifest": manifest, "cfg": cfg, "inp": inp}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", help="path to gap_engine.yaml")
    run(ap.parse_args().config)
