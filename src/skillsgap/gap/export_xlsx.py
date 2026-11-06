"""Build TeamName_Week6_Analysis.xlsx from the engine outputs.

    python src/skillsgap/gap/export_xlsx.py [--out reports/week6/TeamName_Week6_Analysis.xlsx]

Shares, gaps and the STEM ratio are written as Excel formulas over the Joined_Sample sheet,
so every headline number can be traced to the record rows that produce it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from skillsgap.gap import engine as E  # noqa: E402

FONT = "Arial"
HDR = PatternFill("solid", fgColor="1F3A5F")
INPUT = PatternFill("solid", fgColor="FFF2CC")
ENGINE = PatternFill("solid", fgColor="E8EEF5")
WARN = PatternFill("solid", fgColor="FCE4E4")
THIN = Border(bottom=Side(style="thin", color="C9CED6"))


def style_header(ws, row, ncol):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(name=FONT, bold=True, color="FFFFFF")
        cell.fill = HDR
        cell.alignment = Alignment(wrap_text=True, vertical="top")


def set_widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def write_table(ws, df, start_row=1):
    for c, name in enumerate(df.columns, start=1):
        ws.cell(row=start_row, column=c, value=name)
    style_header(ws, start_row, len(df.columns))
    for r, row in enumerate(df.itertuples(index=False), start=start_row + 1):
        for c, v in enumerate(row, start=1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            ws.cell(row=r, column=c, value=v)
    return start_row + len(df)


def fonts(wb):
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                f = cell.font
                cell.font = Font(name=FONT, bold=f.bold, italic=f.italic, color=f.color, size=f.size)


def build(res: dict, out: Path):
    joined, results, cov = res["joined"], res["results"], res["coverage"]
    sens, man, cfg = res["sensitivity"], res["manifest"], res["cfg"]
    wb = Workbook()

    # ---------------------------------------------------------------- README
    ws = wb.active
    ws.title = "README"
    lines = [
        ("Skills-Gap Intelligence Agent - Week 6 gap analysis", True),
        ("Convenience sample: 2 online/district vacancy sources and 2 institutions' 2025 graduation lists. "
         "Results describe this sample only and are NOT national estimates.", False),
        ("", False),
        ("Metric", True),
        ("Demand share D_c = in-scope postings mapped to category c / all mapped in-scope postings", False),
        ("Supply share S_c = graduates mapped to category c / all mapped graduates", False),
        ("Primary gap G_c = 100 x (D_c - S_c), in percentage points. Positive = category is a larger share "
         "of this demand sample than of this graduate sample.", False),
        ("Relative index R_c = D_c / S_c (secondary; blank when S_c = 0).", False),
        ("Categories = Week 4 taxonomy domains DOM-01..DOM-15 (stable IDs). Join key = category_id.", False),
        ("A record mapped to k categories contributes weight 1/k to each, so every record counts once.", False),
        ("", False),
        ("Colour legend", True),
        ("Yellow = editable input (NDPIV ratios). Blue-grey = engine output copied as values "
         "(bootstrap intervals, sensitivity). White = formula over Joined_Sample.", False),
        ("", False),
        ("Versions (from run_manifest.json)", True),
    ]
    for i, (t, b) in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=t).font = Font(name=FONT, bold=b, size=13 if i == 1 else 10)
    r = len(lines) + 1
    keys = ["engine_version", "run_at", "records_file", "records_version", "records_pipeline_version",
            "records_sha256", "taxonomy_source", "taxonomy_version", "taxonomy_review_status",
            "taxonomy_sha256", "extraction_file", "extraction_method_version", "extraction_sha256",
            "mapping_rules_sha256", "categories_sha256", "concept_to_category_sha256", "config_sha256"]
    for k in keys:
        ws.cell(row=r, column=1, value=k).font = Font(name=FONT, bold=True)
        ws.cell(row=r, column=2, value=str(man.get(k, "")))
        r += 1
    set_widths(ws, [34, 90])
    for row in ws.iter_rows(min_row=2, max_row=13):
        row[0].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A2:B2")
    ws.row_dimensions[2].height = 30

    # ---------------------------------------------------------------- Joined_Sample
    wj = wb.create_sheet("Joined_Sample")
    j = joined.copy()
    j["in_share"] = ((j.status == "in_scope") & (j.category_id != E.UNMAPPED)).astype(int)
    cols = ["record_id", "side", "source", "organisation", "text_mapped", "status", "status_detail",
            "duplicate_of", "is_intermediary", "units", "category_id", "category_label", "stem_group", "weight",
            "weighted_units", "in_share", "mapping_basis", "rules_fired", "mapping_certainty", "split_n",
            "count_basis", "field_group_provisional", "award_level", "week5_concepts",
            "week5_agrees_with_rules", "source_url", "retrieved_at", "pipeline_version", "raw_hash",
            "taxonomy_version", "engine_version"]
    j = j[cols].sort_values(["side", "category_id", "record_id"])
    last = write_table(wj, j)
    n = last  # last data row
    for rr in range(2, n + 1):
        if wj.cell(row=rr, column=cols.index("mapping_certainty") + 1).value != "certain":
            wj.cell(row=rr, column=cols.index("mapping_certainty") + 1).fill = WARN
    wj.freeze_panes = "C2"
    wj.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{n}"
    set_widths(wj, [36, 8, 22, 28, 48, 11, 22, 14, 10, 8, 10, 34, 12, 8, 10, 8, 12, 10, 12, 7, 11, 13, 14,
                    16, 10, 40, 11, 9, 20, 9, 13])
    col = {name: get_column_letter(i) for i, name in enumerate(cols, start=1)}
    rng = lambda name: f"Joined_Sample!${col[name]}$2:${col[name]}${n}"  # noqa: E731

    # ---------------------------------------------------------------- Category_Results
    wc = wb.create_sheet("Category_Results")
    head = ["category_id", "category_label", "stem_group", "ict_9274", "demand_units", "demand_records",
            "demand_share", "supply_graduates", "supply_programmes", "supply_share", "gap_pp",
            "ratio_index", "ci_low_pp (engine)", "ci_high_pp (engine)", "sign_robust (engine)",
            "support", "demand_uncertain_share", "supply_uncertain_share", "demand_record_ids",
            "supply_record_ids"]
    for c, h in enumerate(head, start=1):
        wc.cell(row=1, column=c, value=h)
    style_header(wc, 1, len(head))
    nc = len(results)
    tot = nc + 2
    sup = cfg["support"]
    for i, row in enumerate(results.itertuples(index=False), start=2):
        wc.cell(row=i, column=1, value=row.category_id)
        wc.cell(row=i, column=2, value=row.category_label)
        wc.cell(row=i, column=3, value=row.stem_group)
        wc.cell(row=i, column=4, value=row.ict_9274)
        crit = f'{rng("category_id")},$A{i},{rng("in_share")},1'
        wc.cell(row=i, column=5, value=f'=SUMIFS({rng("weighted_units")},{rng("side")},"demand",{crit})')
        wc.cell(row=i, column=6, value=int(row.demand_records))
        wc.cell(row=i, column=7, value=f"=IF($E${tot}=0,0,E{i}/$E${tot})")
        wc.cell(row=i, column=8, value=f'=SUMIFS({rng("weighted_units")},{rng("side")},"supply",{crit})')
        wc.cell(row=i, column=9, value=int(row.supply_programmes))
        wc.cell(row=i, column=10, value=f"=IF($H${tot}=0,0,H{i}/$H${tot})")
        wc.cell(row=i, column=11, value=f"=100*(G{i}-J{i})")
        wc.cell(row=i, column=12, value=f'=IF(J{i}>0,G{i}/J{i},"n/a")')
        for c, v in ((13, row.ci_low_pp), (14, row.ci_high_pp), (15, row.sign_robust)):
            cell = wc.cell(row=i, column=c, value=None if (isinstance(v, float) and pd.isna(v)) else v)
            cell.fill = ENGINE
        wc.cell(row=i, column=16,
                value=(f'=IF(AND(E{i}=0,H{i}=0),"NO EVIDENCE",IF(OR(E{i}<{sup["min_demand_units"]},'
                       f'H{i}<{sup["min_supply_graduates"]}),"LOW SUPPORT","OK"))'))
        wc.cell(row=i, column=17, value=None if pd.isna(row.demand_uncertain_share) else row.demand_uncertain_share)
        wc.cell(row=i, column=18, value=None if pd.isna(row.supply_uncertain_share) else row.supply_uncertain_share)
        wc.cell(row=i, column=19, value=row.demand_record_ids)
        wc.cell(row=i, column=20, value=row.supply_record_ids)
        for c in (7, 10, 17, 18):
            wc.cell(row=i, column=c).number_format = "0.0%"
        for c in (11, 13, 14):
            wc.cell(row=i, column=c).number_format = "+0.0;-0.0;0.0"
        wc.cell(row=i, column=12).number_format = "0.00"
        wc.cell(row=i, column=5).number_format = "0.0"
        wc.cell(row=i, column=8).number_format = "#,##0"
    wc.cell(row=tot, column=1, value="TOTAL (denominator)").font = Font(name=FONT, bold=True)
    for c, f in ((5, f"=SUM(E2:E{tot - 1})"), (7, f"=SUM(G2:G{tot - 1})"), (8, f"=SUM(H2:H{tot - 1})"),
                 (10, f"=SUM(J2:J{tot - 1})"), (11, f"=SUM(K2:K{tot - 1})")):
        cell = wc.cell(row=tot, column=c, value=f)
        cell.font = Font(name=FONT, bold=True)
    wc.cell(row=tot, column=7).number_format = "0.0%"
    wc.cell(row=tot, column=10).number_format = "0.0%"
    wc.cell(row=tot, column=11).number_format = "0.0"
    wc.cell(row=tot + 2, column=1, value=(
        "Gap column sums to 0 by construction. Blue-grey columns: 90% bootstrap interval from the engine "
        f"({cfg['bootstrap']['reps']} resamples of postings and programme rows, seed {cfg['bootstrap']['seed']}). "
        "LOW SUPPORT: fewer than 3 postings or 30 graduates. Do not read LOW SUPPORT rows as findings."))
    wc.merge_cells(start_row=tot + 2, start_column=1, end_row=tot + 2, end_column=12)
    wc.cell(row=tot + 2, column=1).alignment = Alignment(wrap_text=True, vertical="top")
    wc.row_dimensions[tot + 2].height = 42
    wc.freeze_panes = "C2"
    set_widths(wc, [11, 36, 13, 8, 9, 9, 9, 10, 10, 9, 9, 8, 10, 10, 10, 13, 10, 10, 40, 40])
    cat_row = {cid: i for i, cid in enumerate(results.category_id, start=2)}

    # ---------------------------------------------------------------- Worked_Example
    ww = wb.create_sheet("Worked_Example")
    ex = "DOM-10"
    ri = cat_row[ex]
    ww["A1"] = f"Worked example: {ex} Transport, logistics and supply chains"
    ww["A1"].font = Font(name=FONT, bold=True, size=13)
    ww["A2"] = "Every number below is a formula over Joined_Sample or Category_Results."
    exrows = joined[(joined.category_id == ex)][["record_id", "side", "text_mapped", "status", "units",
                                                  "weight", "weighted_units", "rules_fired",
                                                  "mapping_certainty", "source_url"]]
    last = write_table(ww, exrows, start_row=4)
    r = last + 2
    steps = [
        ("Demand units in DOM-10 (in-scope postings x weight)", f"=Category_Results!E{ri}", "0.0"),
        ("All mapped in-scope postings (denominator)", f"=Category_Results!E{tot}", "0.0"),
        ("Demand share D = units / denominator", f"=B{r}/B{r + 1}", "0.0%"),
        ("Graduates in DOM-10", f"=Category_Results!H{ri}", "#,##0"),
        ("All mapped graduates (denominator)", f"=Category_Results!H{tot}", "#,##0"),
        ("Supply share S = graduates / denominator", f"=B{r + 3}/B{r + 4}", "0.0%"),
        ("Gap G = 100 x (D - S), percentage points", f"=100*(B{r + 2}-B{r + 5})", "+0.0;-0.0"),
        ("90% bootstrap interval (engine)", f'=TEXT(Category_Results!M{ri},"+0.0;-0.0")&" to "&'
                                            f'TEXT(Category_Results!N{ri},"+0.0;-0.0")', "@"),
        ("Support label", f"=Category_Results!P{ri}", "@"),
    ]
    for k, (label, f, fmt) in enumerate(steps):
        ww.cell(row=r + k, column=1, value=label).font = Font(name=FONT, bold=True)
        cell = ww.cell(row=r + k, column=2, value=f)
        cell.number_format = fmt
    er = results.set_index("category_id").loc[ex]
    a_ = E.analysable(joined)
    dt, st = a_[a_.side == "demand"].weighted_units.sum(), a_[a_.side == "supply"].weighted_units.sum()
    crosses = er.ci_low_pp <= 0 <= er.ci_high_pp
    ww.cell(row=r + len(steps) + 1, column=1, value=(
        f"Reading: in this sample, {er.demand_units:g} of {dt:g} in-scope postings map to {ex} while "
        f"{er.supply_graduates:,.0f} of {st:,.0f} graduates do. "
        + ("The interval crosses zero, so the sample cannot show that the gap is real."
           if crosses else "The interval excludes zero within this sample only.")))
    ww.merge_cells(start_row=r + len(steps) + 1, start_column=1, end_row=r + len(steps) + 1, end_column=6)
    ww.cell(row=r + len(steps) + 1, column=1).alignment = Alignment(wrap_text=True)
    ww.row_dimensions[r + len(steps) + 1].height = 45
    set_widths(ww, [52, 16, 46, 10, 8, 8, 10, 10, 12, 45])

    # ---------------------------------------------------------------- STEM_Ratio
    wr = wb.create_sheet("STEM_Ratio")
    wr["A1"] = "NDPIV para 441(iv) (cited as 441(ii) in the brief): Science & Technology to humanities graduates, as x : 5"
    wr["A1"].font = Font(name=FONT, bold=True, size=13)
    cur, tgt = cfg["ndpiv_441ii"]["current_stem_to_humanities"], cfg["ndpiv_441ii"]["target_stem_to_humanities"]
    wr["A3"], wr["B3"], wr["C3"] = "NDPIV baseline FY2022/23 (STEM : humanities)", cur[0], cur[1]
    wr["A4"], wr["B4"], wr["C4"] = "NDPIV target 2029/30 (STEM : humanities)", tgt[0], tgt[1]
    for a in ("B3", "C3", "B4", "C4"):
        wr[a].fill = INPUT
        wr[a].font = Font(name=FONT, color="0000FF")
    wr["D3"], wr["D4"] = "=5*B3/C3", "=5*B4/C4"
    wr["E3"] = "Source: NDPIV FY2025/26-2029/30, para 441(iv), printed p. 200 (PDF p. 237): 2:5 in FY2022/23 to 3:5 by 2029/30"
    head = ["variant", "STEM graduates", "humanities graduates", "health graduates (held out)",
            "STEM per 5 humanities", "vs NDPIV current (x:5)", "vs NDPIV target (x:5)",
            "comparable to NDPIV?", "note"]
    for c, h in enumerate(head, start=1):
        wr.cell(row=6, column=c, value=h)
    style_header(wr, 6, len(head))
    base = f'{rng("side")},"supply",{rng("in_share")},1'

    def S(group, extra=""):
        return f'SUMIFS({rng("weighted_units")},{base},{rng("field_group_provisional")},"{group}"{extra})'

    inst = sorted(joined[joined.side == "supply"].organisation.dropna().unique())
    variants = [
        ("Primary: health held out", S("STEM"), S("NON_STEM"), S("REVIEW_HEALTH"),
         "NO - two-institution convenience sample", "NON_STEM used as humanities (Week 4 MAP-004 caveat)"),
        ("Health counted as STEM", f'{S("STEM")}+{S("REVIEW_HEALTH")}', S("NON_STEM"), "0",
         "NO", "Sensitivity for MAP-006"),
        ("Health counted as humanities", S("STEM"), f'{S("NON_STEM")}+{S("REVIEW_HEALTH")}', "0",
         "NO", "Sensitivity for MAP-006"),
        ("Exact counts only", S("STEM", f',{rng("count_basis")},"exact"'),
         S("NON_STEM", f',{rng("count_basis")},"exact"'), S("REVIEW_HEALTH", f',{rng("count_basis")},"exact"'),
         "NO", "Drops approx and combined counts: all IUIU rows and both UMI ICT rows"),
    ] + [(f"Institution: {x}", S("STEM", f',{rng("organisation")},"{x}"'),
          S("NON_STEM", f',{rng("organisation")},"{x}"'),
          S("REVIEW_HEALTH", f',{rng("organisation")},"{x}"'), "NO", "Single institution") for x in inst]
    for k, (name, fs, fh, fx, comp, note) in enumerate(variants, start=7):
        wr.cell(row=k, column=1, value=name)
        wr.cell(row=k, column=2, value=f"={fs}").number_format = "#,##0"
        wr.cell(row=k, column=3, value=f"={fh}").number_format = "#,##0"
        wr.cell(row=k, column=4, value=f"={fx}").number_format = "#,##0"
        wr.cell(row=k, column=5, value=f'=IF(C{k}=0,"n/a",5*B{k}/C{k})').number_format = "0.00"
        wr.cell(row=k, column=6, value=f'=IF(C{k}=0,"n/a",E{k}-$D$3)').number_format = "+0.00;-0.00"
        wr.cell(row=k, column=7, value=f'=IF(C{k}=0,"n/a",E{k}-$D$4)').number_format = "+0.00;-0.00"
        wr.cell(row=k, column=8, value=comp)
        wr.cell(row=k, column=9, value=note)
    k = 7 + len(variants)
    dbase = f'{rng("side")},"demand",{rng("in_share")},1'
    wr.cell(row=k, column=1, value="Demand analogue: postings in STEM vs non-STEM categories")
    wr.cell(row=k, column=2, value=f'=SUMIFS({rng("weighted_units")},{dbase},{rng("stem_group")},"STEM")')
    wr.cell(row=k, column=3, value=f'=SUMIFS({rng("weighted_units")},{dbase},{rng("stem_group")},"NON_STEM")')
    wr.cell(row=k, column=4, value=f'=SUMIFS({rng("weighted_units")},{dbase},{rng("stem_group")},"REVIEW_HEALTH")')
    wr.cell(row=k, column=5, value=f'=IF(C{k}=0,"n/a",5*B{k}/C{k})').number_format = "0.00"
    wr.cell(row=k, column=8, value="NO - counts postings, not graduates")
    wr.cell(row=k, column=9, value="Units are postings; shown only to contrast the demand mix with the supply mix")
    for c in (2, 3, 4):
        wr.cell(row=k, column=c).number_format = "0.0"
    wr.cell(row=k + 2, column=1, value=(
        "Interpretation: the supply sample's ratio is far below NDPIV's 2:5, but the sample is a management "
        "institute and the law/business campus of one university, so the gap reflects which institutions were "
        "collected, not the national graduate mix. NOT COMPARABLE as a national estimate."))
    wr.merge_cells(start_row=k + 2, start_column=1, end_row=k + 2, end_column=9)
    wr.cell(row=k + 2, column=1).alignment = Alignment(wrap_text=True)
    wr.row_dimensions[k + 2].height = 45
    set_widths(wr, [52, 12, 13, 13, 12, 13, 13, 30, 60])

    # ---------------------------------------------------------------- Sensitivity
    wsn = wb.create_sheet("Sensitivity")
    piv = sens.pivot(index="category_id", columns="scenario", values="gap_pp").reset_index()
    piv.insert(1, "category_label", piv.category_id.map(results.set_index("category_id").category_label))
    write_table(wsn, piv)
    for row in wsn.iter_rows(min_row=2, min_col=3):
        for cell in row:
            cell.number_format = "+0.0;-0.0;0.0"
            cell.fill = ENGINE
    tots = sens.drop_duplicates("scenario")[["scenario", "demand_units_total", "supply_graduates_total"]]
    r0 = len(piv) + 3
    wsn.cell(row=r0, column=1, value="Denominators per scenario").font = Font(name=FONT, bold=True)
    write_table(wsn, tots, start_row=r0 + 1)
    set_widths(wsn, [11, 36] + [16] * 7)
    for c in range(3, 10):
        wsn.cell(row=1, column=c).alignment = Alignment(wrap_text=True, vertical="top")
    wsn.row_dimensions[1].height = 45

    # ---------------------------------------------------------------- Coverage & exceptions
    wv = wb.create_sheet("Coverage")
    write_table(wv, cov)
    set_widths(wv, [10] + [13] * 12)
    wv.row_dimensions[1].height = 45
    for c in range(1, 14):
        wv.cell(row=1, column=c).alignment = Alignment(wrap_text=True, vertical="top")
    wx = wb.create_sheet("Unmatched_Uncertain")
    exc = joined[(joined.category_id == E.UNMAPPED) | (joined.mapping_certainty != "certain") |
                 (joined.status != "in_scope")][["record_id", "side", "text_mapped", "status", "status_detail",
                                                 "category_id", "weight", "rules_fired", "mapping_certainty",
                                                 "week5_concepts"]]
    write_table(wx, exc)
    set_widths(wx, [36, 8, 52, 12, 24, 10, 8, 10, 12, 14])

    fonts(wb)
    for wsx in wb.worksheets:
        for c in range(1, wsx.max_column + 1):
            h = wsx.cell(row=1, column=c)
            if h.fill == HDR:
                h.font = Font(name=FONT, bold=True, color="FFFFFF")
    wb["Category_Results"]["M1"].comment = Comment("Engine output (values), not a formula.", "engine")
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--out", default=str(E.REPO_ROOT / "reports" / "week6" / "TeamName_Week6_Analysis.xlsx"))
    a = ap.parse_args()
    print(f"Workbook -> {build(E.run(a.config), Path(a.out))}")
