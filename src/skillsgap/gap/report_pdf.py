"""Build TeamName_Week6_Methodology.pdf from the engine outputs.

    python src/skillsgap/gap/report_pdf.py [--out reports/week6/TeamName_Week6_Methodology.pdf]

All figures in the report are read from the engine run, so a re-run on new data updates them.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (Flowable, Image, KeepTogether, PageBreak, Paragraph,  # noqa: E402
                                SimpleDocTemplate, Spacer, Table, TableStyle)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from skillsgap.gap import engine as E  # noqa: E402

BLUE, RED, INK, MUTED, GRID = "#2a78d6", "#e34948", "#0b0b0b", "#52514e", "#d9d8d4"
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=15, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=11.5,
                    spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1F3A5F"))
BODY = ParagraphStyle("B", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.4, leading=12.6,
                      alignment=TA_LEFT, spaceAfter=5)
SMALL = ParagraphStyle("S", parent=BODY, fontSize=8, leading=10, textColor=colors.HexColor(MUTED))
CELL = ParagraphStyle("C", parent=BODY, fontSize=8, leading=9.8, spaceAfter=0)
MONO = ParagraphStyle("M", parent=BODY, fontName="Courier", fontSize=8, leading=10)


def P(t, s=BODY):
    return Paragraph(t, s)


def table(rows, widths, header=True, zebra=True):
    data = [[c if isinstance(c, Flowable) else P(str(c), CELL) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor(GRID)),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
        for i in range(len(rows[0])):
            data[0][i] = P(f"<b><font color='white'>{rows[0][i]}</font></b>", CELL)
        t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(st))
    return t


def pp(x, sign=True):
    return "n/a" if pd.isna(x) else (f"{x:+.1f}" if sign else f"{x:.1f}")


def pct(x):
    return "n/a" if pd.isna(x) else f"{100 * x:.1f}%"


# --------------------------------------------------------------------------- figure
def gap_figure(results: pd.DataFrame, path: Path):
    r = results[results.support != "NO EVIDENCE"].sort_values("gap_pp")
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    y = range(len(r))
    for i, row in enumerate(r.itertuples()):
        c = BLUE if row.gap_pp > 0 else RED
        ax.plot([row.ci_low_pp, row.ci_high_pp], [i, i], color=c, lw=2, alpha=0.35,
                solid_capstyle="round")
        ax.plot(row.gap_pp, i, "o", ms=7, color=c, mec="#fcfcfb", mew=2)
        ax.text(row.ci_high_pp + 1.2, i, f"{row.gap_pp:+.1f}", va="center", fontsize=7.5, color=INK)
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{c}  {l[:44]}" for c, l in zip(r.category_id, r.category_label)],
                       fontsize=7.5, color=INK)
    ax.set_xlabel("Gap G = demand share - supply share (percentage points); line = 90% bootstrap interval",
                  fontsize=7.5, color=MUTED)
    ax.tick_params(axis="x", labelsize=7.5, colors=MUTED)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, lw=0.5)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Blue: larger share of the demand sample.  Red: larger share of the graduate sample.",
                 loc="left", fontsize=7.5, color=MUTED)
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


# --------------------------------------------------------------------------- wireframe
class Wireframe(Flowable):
    """Low-fidelity Week 7 screen: one category result with definition, counts, provenance, limits."""

    def __init__(self, w=17 * cm, h=10.4 * cm, ex=None):
        super().__init__()
        self.w, self.h, self.ex = w, h, ex

    def wrap(self, *a):
        return self.w, self.h

    def box(self, c, x, y, w, h, title=None, fill="#ffffff"):
        c.setFillColor(colors.HexColor(fill))
        c.setStrokeColor(colors.HexColor("#8a8984"))
        c.setLineWidth(0.6)
        c.roundRect(x, y, w, h, 3, stroke=1, fill=1)
        if title:
            c.setFillColor(colors.HexColor("#1F3A5F"))
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(x + 5, y + h - 10, title)

    def lines(self, c, x, y, items, size=6.8, gap=9):
        c.setFont("Helvetica", size)
        c.setFillColor(colors.HexColor(INK))
        for i, t in enumerate(items):
            c.drawString(x, y - i * gap, t)

    def draw(self):
        c, w, h, ex = self.canv, self.w, self.h, self.ex
        self.box(c, 0, 0, w, h, fill="#f5f5f3")
        c.setFillColor(colors.HexColor("#1F3A5F"))
        c.rect(0, h - 22, w, 22, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(8, h - 15, "Skills-Gap Intelligence Agent  |  Category view")
        c.setFont("Helvetica", 7)
        c.drawRightString(w - 8, h - 15, f"Data: {ex['data_tag']}   Taxonomy v{ex['tax']}   Engine {ex['eng']}")
        # banner
        c.setFillColor(colors.HexColor("#FCE4E4"))
        c.rect(6, h - 40, w - 12, 14, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#8a1c1c"))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(10, h - 36, "Sample result, not a national estimate: "
                     f"{ex['nd']:g} postings and {ex['ns']:,.0f} graduates from 2 institutions.")
        # category picker
        self.box(c, 6, h - 112, 120, 66, "Category")
        self.lines(c, 12, h - 70, [f"> {ex['cid']} (selected)", "  DOM-06", "  DOM-07", "  DOM-02  ...",
                                   "[ ] hide LOW SUPPORT"])
        # result card
        x0 = 132
        self.box(c, x0, h - 112, w - x0 - 6, 66, f"{ex['cid']}  {ex['label']}")
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(colors.HexColor(BLUE if ex['gap'] > 0 else RED))
        c.drawString(x0 + 8, h - 84, f"{ex['gap']:+.1f} pp")
        c.setFont("Helvetica", 6.8)
        c.setFillColor(colors.HexColor(INK))
        c.drawString(x0 + 8, h - 96, f"90% interval {ex['lo']:+.1f} to {ex['hi']:+.1f}  |  {ex['support']}")
        c.drawString(x0 + 8, h - 106, "Interval crosses 0: direction not established in this sample")
        bx, bw = x0 + 205, w - x0 - 220
        for i, (lab, v, col) in enumerate((("Demand share", ex['D'], BLUE), ("Supply share", ex['S'], RED))):
            yy = h - 72 - i * 18
            c.setFillColor(colors.HexColor(MUTED))
            c.drawString(bx, yy + 3, f"{lab} {100 * v:.1f}%")
            c.setFillColor(colors.HexColor("#e6e5e1"))
            c.rect(bx + 78, yy + 1, bw - 78, 7, stroke=0, fill=1)
            c.setFillColor(colors.HexColor(col))
            c.rect(bx + 78, yy + 1, (bw - 78) * min(v / 0.6, 1), 7, stroke=0, fill=1)
        # definition + counts
        half = (w - 18) / 2
        self.box(c, 6, h - 196, half, 78, "Definition")
        self.lines(c, 12, h - 140, ["Gap = 100 x (demand share - supply share)",
                                    "Demand share = postings in category / all postings",
                                    "Supply share = graduates in category / all graduates",
                                    "Multi-category records split equally (count once)",
                                    "[Read full method]"])
        self.box(c, 12 + half, h - 196, half, 78, "Supporting counts")
        self.lines(c, 18 + half, h - 140, [f"Postings in category: {ex['du']:g} of {ex['nd']:g}",
                                           f"Graduates in category: {ex['su']:,.0f} of {ex['ns']:,.0f}",
                                           f"Uncertain mappings: {ex['unc']}",
                                           f"Sensitivity: sign holds in {ex['hold']}",
                                           "[Show records table]"])
        # provenance + limitations
        self.box(c, 6, h - 280, half, 78, "Provenance")
        self.lines(c, 12, h - 224, ["Sources: brightermonday.co.ug/jobs, lyantonde.go.ug,",
                                    "  umi.ac.ug graduation list 2025",
                                    "Retrieved 2026-10-21 (manual capture)",
                                    f"Records file sha256 {ex['sha'][:16]}...",
                                    "[Download joined rows CSV]"])
        self.box(c, 12 + half, h - 280, half, 78, "Limitations for this result")
        self.lines(c, 18 + half, h - 224, ["Only 2 postings in this category",
                                           "Online postings miss informal work",
                                           "Supply = 2 institutions, mostly postgraduate",
                                           "Mapping rules are provisional (taxonomy v0.1)",
                                           "[All limitations]"])
        c.setFont("Helvetica-Oblique", 6.5)
        c.setFillColor(colors.HexColor(MUTED))
        c.drawString(8, 6, "Wireframe only. Every number on the card links to the Joined_Sample rows that produce it.")


# --------------------------------------------------------------------------- report
def build(res: dict, out: Path):
    j, results, cov, ratio = res["joined"], res["results"], res["coverage"], res["ratio"]
    sens, man, cfg = res["sensitivity"], res["manifest"], res["cfg"]
    a = E.analysable(j)
    nd, ns = a[a.side == "demand"].weighted_units.sum(), a[a.side == "supply"].weighted_units.sum()
    cd, cs = cov.set_index("side").loc["demand"], cov.set_index("side").loc["supply"]
    r = results.set_index("category_id")
    ev = results[results.support != "NO EVIDENCE"].sort_values("gap_pp")
    top_pos, top_neg = ev.iloc[-1], ev.iloc[0]
    no_ev = results[results.support == "NO EVIDENCE"].category_id.tolist()
    rp = ratio.set_index("variant")
    prim = rp.loc["Primary: supply, health excluded"]
    hstem = rp.loc["Health counted as STEM"]
    dem = ratio[ratio.variant.str.startswith("Demand")].iloc[0]
    piv = sens.pivot(index="category_id", columns="scenario", values="gap_pp")
    scen = list(piv.columns)

    def sign_hold(cid):
        s0 = piv.at[cid, "S0 primary"]
        return sum((piv.at[cid, sc] > 0) == (s0 > 0) and abs(piv.at[cid, sc]) > 1e-9 for sc in scen)

    rec = j.drop_duplicates("record_id")
    bm = rec[(rec.source == "brightermonday")]
    n_bm, n_int = len(bm), int(bm.is_intermediary.sum())
    strict = ev[(ev.ci_low_pp > 0) | (ev.ci_high_pp < 0)]
    excl_txt = ("Every 90% interval includes zero, so no category gap is established."
                if strict.empty else
                "Only " + ", ".join(f"{x.category_id} ({x.demand_units:g} postings, {x.supply_graduates:,.0f} graduates)"
                                   for x in strict.itertuples()) +
                " has an interval excluding zero, and it is LOW SUPPORT, so no category gap is established."
                if (strict.support != "OK").all() else
                "Intervals excluding zero: " + ", ".join(strict.category_id) + ".")
    fig = out.parent / "week6_gap_chart.png"
    gap_figure(results, fig)
    ex = "DOM-10"
    exr = r.loc[ex]
    agree = man["week5_agreement"]
    story = []
    S = story.append

    S(P("Week 6 Methodology: Supply-Demand Gap Analysis", H1))
    S(P("Skills-Gap Intelligence Agent, MSD7303, Muni University. Team: Ayiko Mike, Aseki Ali, Andema Agusto. "
        f"Supervisor: Dr. Andogah Geoffrey. Engine {man['engine_version']}, run {man['run_at'][:10]}.", SMALL))
    S(P("<b>Bottom line.</b> The engine joins online vacancy postings and published graduate counts on Week 4 "
        f"taxonomy domains and reports, for each domain, the gap between its share of demand and its share of "
        f"supply. On the current sample ({nd:g} postings, {ns:,.0f} graduates) the largest positive gap is "
        f"{top_pos.category_id} {top_pos.category_label} ({pp(top_pos.gap_pp)} pp) and the largest negative gap is "
        f"{top_neg.category_id} {top_neg.category_label} ({pp(top_neg.gap_pp)} pp). " + excl_txt + " The sample's STEM-to-humanities "
        f"ratio is {prim.stem_per_5_humanities:.2f}:5 against NDPIV's 2:5 current and 3:5 target; this is not "
        "comparable, because the supply sample is two management/law-heavy institutions. The value of Week 6 is a "
        "working, traceable engine that will produce defensible numbers once Week 3 collection reaches the "
        "charter's 2,000 postings.", BODY))

    S(P("1. Versions that produced this result", H2))
    S(table([["Input", "Version / file", "SHA-256 (first 16)"],
             ["Demand + supply records (Week 3)", f"{man['records_file']} ({man['records_version']})",
              man["records_sha256"][:16]],
             ["Taxonomy (Week 4)", f"{man['taxonomy_source']}, v{man['taxonomy_version']}, "
                                   f"{man['taxonomy_review_status']}", man["taxonomy_sha256"][:16]],
             ["Extraction output (Week 5)", f"{man['extraction_file']}, {man['extraction_method_version']}",
              man["extraction_sha256"][:16]],
             ["Mapping rules (Week 6)", "config/week6/mapping_rules.csv", man["mapping_rules_sha256"][:16]],
             ["Category attributes", "config/week6/categories.csv", man["categories_sha256"][:16]],
             ["Engine config", "config/week6/gap_engine.yaml", man["config_sha256"][:16]]],
            [4.3 * cm, 9.2 * cm, 3.5 * cm]))
    S(P("The Week 8 held-out split (17 records) is excluded by design and the engine refuses to read it, so Week 8 "
        "extraction evaluation stays clean. run_manifest.json stores every hash above plus the hash of every output.",
        SMALL))

    S(P("2. Units, population, geography and period", H2))
    S(table([["", "Demand", "Supply"],
             ["Unit", "One de-duplicated online or district vacancy posting", "One graduate on a published graduation list"],
             ["Population", "Postings captured from BrighterMonday (12) and Lyantonde District (3) for jobs in Uganda",
              "Graduates of UMI 22nd ceremonies and IUIU 34th ceremony (Kampala campus)"],
             ["Geography", "Uganda; 2 postings located outside Uganda are out of scope",
              "Kampala-based campuses of 2 institutions"],
             ["Period", "Posted 7-21 Oct 2026 (estimated from relative dates); retrieved 21 Oct 2026",
              "Ceremonies Mar-Apr 2025 (UMI) and 20 Dec 2025 (IUIU)"],
             ["Numerator", "Postings mapped to category c (fractional)", "Graduates mapped to category c (fractional)"],
             ["Denominator", f"All mapped in-scope postings: {nd:g}", f"All mapped graduates: {ns:,.0f}"],
             ["Aggregation", "Sum of weights by Week 4 domain", "Sum of graduate_count x weight by Week 4 domain"]],
            [2.6 * cm, 7.2 * cm, 7.2 * cm]))
    S(P("Postings are counted once each, not by number of positions, because BrighterMonday does not publish a "
        "vacancy count (12 of 15 missing). The demand and supply periods differ by about a year; graduates of 2025 "
        "are treated as the supply entering the 2026 market.", SMALL))

    S(P("3. Primary gap formula and why", H2))
    S(P("For each category c: <b>D<sub>c</sub></b> = demand units in c / all mapped demand units; "
        "<b>S<sub>c</sub></b> = graduates in c / all mapped graduates; "
        "<b>G<sub>c</sub> = 100 &times; (D<sub>c</sub> &minus; S<sub>c</sub>)</b> percentage points. "
        "A positive gap means the category is a larger share of the demand sample than of the graduate sample "
        "(possible under-supply relative to this demand); a negative gap means the reverse.", BODY))
    S(P("Why a share difference: postings and graduates are different units with very different totals, so raw "
        "counts cannot be subtracted; shares put both on a 0-1 scale. The difference is defined when one side is "
        "zero (common here), is bounded, sums to zero across categories, and reads directly in percentage points "
        "for a policy audience. The ratio R<sub>c</sub> = D<sub>c</sub>/S<sub>c</sub> is reported as a secondary "
        "index only, because it is undefined at S<sub>c</sub> = 0 and explodes for tiny supply shares. A category "
        f"with fewer than {cfg['support']['min_demand_units']} postings or {cfg['support']['min_supply_graduates']} "
        "graduates is labelled LOW SUPPORT and must not be presented as a finding.", BODY))

    S(P("4. Join, mapping and data treatment", H2))
    S(P("<b>Join key.</b> Both sides are mapped to Week 4 taxonomy domain IDs (DOM-01 to DOM-15), which are stable "
        "concept IDs, and joined on <font name='Courier'>category_id</font>. Domains were chosen over occupations "
        "because supply records are programmes, which do not map to ISCO occupations, and because Week 5 found no "
        "demand-side skill text to join at skill level (posting descriptions are empty).", BODY))
    S(P("<b>Mapping.</b> Versioned regular-expression rules (config/week6/mapping_rules.csv) map each posting title "
        "and programme title to domains, citing the taxonomy alias each rule relies on. Only the highest-priority "
        "matches are kept, so a specific rule (\"public administration\" to DOM-07) beats a generic one "
        "(\"administration\" to DOM-06), which avoids the domain over-matching Week 5 reported. Week 5 extraction is "
        f"used as an independent cross-check: where it produced a reviewed occupation or skill, its domain agrees "
        f"with the rule mapping for {agree['agree']} of {agree['records_with_week5_evidence']} records. Running the "
        "gap with Week 5 mappings first is sensitivity S5.", BODY))
    S(P("<b>Multi-category records.</b> A record matching k categories at the top priority contributes 1/k to each "
        f"(fractional counting), so every record counts exactly once. {int(cd.split_records)} posting and "
        f"{int(cs.split_records)} programme rows are split, for example \"Pharmaceutical and Medical Sales "
        "Representative\" (half DOM-04, half DOM-06).", BODY))
    S(P(f"<b>Uncertain mappings.</b> A mapping is uncertain when its rule is marked uncertain, when the record is "
        f"split, or when a combined graduate count spans categories. {int(cd.uncertain_records)} of {int(nd)} postings "
        f"and {int(cs.uncertain_records)} of {int(cs.analysed_records)} programmes are uncertain (listed in "
        "Unmatched_Uncertain). The largest is Bachelor of Laws (329 graduates) mapped to DOM-07, because taxonomy "
        "v0.1 has no legal domain. Sensitivity S1 drops all uncertain records.", BODY))
    S(P(f"<b>Duplicates and missing data.</b> Duplicates are detected by title + employer (demand), institution + "
        f"ceremony + programme (supply) and by raw_hash; none were found ({int(cd.excluded_duplicate)} + "
        f"{int(cs.excluded_duplicate)}). Possible re-posts by intermediaries (BrighterMonday Consulting, Anonymous "
        "Employer) are kept but flagged and tested in S3. Records with no title or no graduate count would be "
        "excluded and listed (none here). Approximate counts (all IUIU rows) are kept and tested in S4. "
        f"Unmatched: {int(cd.unmapped_in_scope)} postings and {int(cs.unmapped_in_scope)} programmes failed to map; "
        f"categories with no evidence on either side: {', '.join(no_ev)}.", BODY))

    S(P("5. Worked example: " + f"{ex} {exr.category_label}", H2))
    S(table([["Step", "Value", "Source"],
             ["Postings mapped to DOM-10", f"{exr.demand_units:g}", "Procurement Officer; Stock/Inventory Manager (rules D01, D02)"],
             ["All mapped in-scope postings", f"{nd:g}", "Coverage sheet"],
             ["Demand share D", pct(exr.demand_share), f"{exr.demand_units:g} / {nd:g}"],
             ["Graduates mapped to DOM-10", f"{exr.supply_graduates:,.0f}", "UMI PGD Procurement and Supply Chain (127) + PGD Logistics and Transport (60), rule S08"],
             ["All mapped graduates", f"{ns:,.0f}", "Coverage sheet"],
             ["Supply share S", pct(exr.supply_share), f"{exr.supply_graduates:,.0f} / {ns:,.0f}"],
             ["Gap G = 100(D - S)", f"{exr.gap_pp:+.1f} pp", "Category_Results row DOM-10"],
             ["90% bootstrap interval", f"{exr.ci_low_pp:+.1f} to {exr.ci_high_pp:+.1f}", "Crosses zero"],
             ["Support", exr.support, "Only 2 postings"]],
            [4.6 * cm, 3.0 * cm, 9.4 * cm]))
    S(P("Each row traces to record IDs, source URLs and retrieval dates in the Joined_Sample sheet. The Week 4 "
        "taxonomy lists procurement under DOM-06 skills (SKL-038) but logistics and supply chains under DOM-10; the "
        "rule follows the DOM-10 alias, which is a documented taxonomy choice.", SMALL))

    S(P("6. Results by category", H2))
    rows = [["Category", "Posts", "D", "Grads", "S", "Gap pp", "90% interval", "Support"]]
    for x in results.sort_values("gap_pp", ascending=False).itertuples():
        if x.support == "NO EVIDENCE":
            continue
        rows.append([f"{x.category_id} {x.category_label}", f"{x.demand_units:g}", pct(x.demand_share),
                     f"{x.supply_graduates:,.0f}", pct(x.supply_share), pp(x.gap_pp),
                     f"{pp(x.ci_low_pp)} to {pp(x.ci_high_pp)}", x.support])
    rows.append([f"No evidence either side: {', '.join(no_ev)}", "0", "0%", "0", "0%", "0", "", "NO EVIDENCE"])
    rows.append(["Total (denominator)", f"{nd:g}", "100%", f"{ns:,.0f}", "100%", "0", "", ""])
    S(table(rows, [5.0 * cm, 1.6 * cm, 1.3 * cm, 1.8 * cm, 1.3 * cm, 1.4 * cm, 2.4 * cm, 2.2 * cm]))
    S(Spacer(1, 4))
    S(Image(str(fig), width=17 * cm, height=17 * cm * 3.6 / 7.2))
    S(P("Only DOM-06 Business, finance and administration has adequate support; its gap is negative but its "
        f"interval runs from {pp(r.at['DOM-06', 'ci_low_pp'])} to {pp(r.at['DOM-06', 'ci_high_pp'])} pp and its sign "
        f"flips in {len(scen) - sign_hold('DOM-06')} of {len(scen)} scenarios. " + " ".join(f"The {x.category_id} interval excludes zero only because it has {x.demand_units:g} postings and "
                    f"{x.supply_graduates:,.0f} graduates; it is LOW SUPPORT and not a finding." for x in strict.itertuples()), BODY))

    S(P("7. STEM-to-humanities comparison with NDPIV para 441(iv) (cited as 441(ii) in the brief)", H2))
    S(P("<b>Source text.</b> NDPIV paragraph 441, item (iv) (printed p. 200, PDF p. 237) sets the programme result "
        "\"Increased ratio of Science and Technology graduates to humanities graduates from 2:5 in FY2022/23 to "
        "3:5\". Item (ii) of the same paragraph is the unemployment target (11.9% to 8.1%), so the brief's "
        "\"441(ii)\" appears to refer to item (iv). The benchmark is therefore a ratio of <i>graduates</i>, with a "
        "FY2022/23 baseline. The Plan is not consistent elsewhere: printed p. 8 (PDF p. 45) describes a ratio of humanities to "
        "science <i>courses</i> of 2:5, and printed pp. 11 and 108 say the STEM-to-humanities graduate ratio has "
        "stagnated at 2:5. We use the programme result in 441(iv) as the operative definition.", BODY))
    rows = [["Measure", "STEM", "Humanities", "STEM per 5 humanities", "Comparable?"]]
    for x in ratio.itertuples():
        rows.append([x.variant, f"{x.stem_graduates:,.1f}".rstrip("0").rstrip("."),
                     f"{x.humanities_graduates:,.1f}".rstrip("0").rstrip("."),
                     "n/a" if pd.isna(x.stem_per_5_humanities) else f"{x.stem_per_5_humanities:.2f} : 5",
                     x.comparable_to_ndpiv])
    rows += [["NDPIV baseline FY2022/23 (441(iv))", "", "", "2 : 5", "Policy benchmark"],
             ["NDPIV target 2029/30 (441(iv))", "", "", "3 : 5", "Policy benchmark"]]
    S(table(rows, [6.6 * cm, 1.6 * cm, 2.0 * cm, 3.0 * cm, 3.8 * cm]))
    S(P(f"<b>Result.</b> The supply sample has {prim.stem_graduates:.0f} STEM and {prim.humanities_graduates:,.0f} "
        f"humanities graduates (health held out), a ratio of {prim.stem_per_5_humanities:.2f}:5, roughly a fifth of "
        f"NDPIV's 2:5 baseline. Counting the {int(prim.health_graduates_excluded)} health graduates as STEM raises it "
        f"to {hstem.stem_per_5_humanities:.2f}:5, still below 2:5.", BODY))
    S(P("<b>Why it diverges, and why it is labelled non-comparable.</b> (1) Selection: UMI is a management institute "
        "and IUIU's Kampala campus mainly awards law, business and administration, so the sample excludes the "
        "universities where most science and engineering graduates qualify. (2) Level and period: most UMI awards are "
        "postgraduate diplomas from 2025 ceremonies, while the NDPIV baseline is a national FY2022/23 figure for "
        "all graduates. "
        "(3) Definition: the sample uses Week 3's provisional STEM/NON_STEM flag and treats all NON_STEM as "
        "humanities, which MAP-004 warns against; health is unresolved (MAP-006). (4) Counts: all IUIU counts are "
        "approximate, and both UMI ICT rows are combined counts. The comparison therefore tests the engine, not "
        "the policy claim. The demand analogue "
        f"({dem.stem_per_5_humanities:.2f}:5, counted in postings) is shown only to contrast the two mixes and is "
        "not an NDPIV measure. NDPIV also names \"Science and Technology\", not STEM; whether health and "
        "agriculture count as science is not defined in 441(iv), which is why the health variants are reported.", BODY))

    S(P("8. NDPIV ICT demand statement (cited as 9274 in the brief)", H2))
    S(P("<b>Source text.</b> The statement sits in paragraph 383 (printed p. 177, PDF p. 214), on human resource capacity for the "
        "digital economy. It says ICT graduates are not yet meeting private-sector demand and lack practical "
        "skills in AI, blockchain, cloud computing and cybersecurity. The same paragraph names UMI among the "
        "institutions training ICT professionals, and notes Makerere alone produced over 2,100 ICT graduates in "
        "five years. NDPIV has no paragraph 9274; the number most likely refers to a line in a text copy of the "
        "Plan.", BODY))
    S(P(f"In this sample "
        f"{r.at['DOM-02', 'demand_units']:g} of {nd:g} postings is an ICT role (MIS Associate) and "
        f"{r.at['DOM-02', 'supply_graduates']:,.0f} of {ns:,.0f} graduates hold ICT awards, a gap of "
        f"{pp(r.at['DOM-02', 'gap_pp'])} pp with interval {pp(r.at['DOM-02', 'ci_low_pp'])} to "
        f"{pp(r.at['DOM-02', 'ci_high_pp'])} pp. One posting cannot support any statement about ICT demand. "
        "Paragraph 383 is also a claim about skills quality, not numbers: testing it needs employer-required skill "
        "mentions such as cloud computing (SKL-013), machine learning (SKL-007) and cybersecurity (SKL-020), all "
        "already in the Week 4 taxonomy, extracted from posting descriptions. Week 5 found every description "
        "empty, so the data cannot test the statement until posting bodies are collected.", BODY))

    S(P("9. Robustness checks", H2))
    S(P(f"<b>Bootstrap.</b> Postings and programme rows were resampled independently with replacement "
        f"({cfg['bootstrap']['reps']} times, seed {cfg['bootstrap']['seed']}) to give 90% intervals. Their width "
        "(tens of percentage points) is the main reasonableness check: with 13 postings, one posting moves a demand "
        "share by 7.7 pp.", BODY))
    srows = [["Category"] + [s.split(" ", 1)[0] for s in scen] + ["Sign holds"]]
    for cid in ev.category_id:
        srows.append([cid] + [pp(piv.at[cid, s]) for s in scen] + [f"{sign_hold(cid)} of {len(scen)}"])
    S(table(srows, [1.8 * cm] + [1.85 * cm] * len(scen) + [2.0 * cm]))
    S(P("S0 primary; S1 certain mappings only; S2 include jobs outside Uganda; S3 exclude intermediary employers; "
        "S4 exact supply counts only; S5 Week 5 extraction mapping first; S6 drop the two largest programmes "
        "(PGD Project Planning 578, PGD M&amp;E 556). DOM-06's sign depends on the choices (S5, S6), so its "
        "direction is not robust. DOM-07 stays negative in every scenario, driven by public administration and law "
        "graduates, but its interval still crosses zero.", SMALL))

    S(P("10. Limitations and bias", H2))
    for t in [
        "<b>Convenience sample, not a national estimate.</b> 13 postings from one job board and one district, and "
        "graduates of two institutions. No figure here describes the Ugandan labour market or graduate output.",
        f"<b>Source bias.</b> Online postings over-represent formal, urban, white-collar jobs; {n_int} of {n_bm} BrighterMonday "
        "postings come from intermediaries. Supply is postgraduate- and management-heavy.",
        "<b>Informal-sector blind spot.</b> No posting evidences DOM-13 informal work, where most Ugandans work; the "
        "gap for informal skills is unknown, not zero.",
        "<b>Publication lag.</b> Supply is 2025 ceremonies, demand is October 2026; graduation lists appear months "
        "after ceremonies and national statistics (NCHE, UBOS) lag further.",
        "<b>Extraction errors.</b> Week 5 v1 recall is limited to taxonomy aliases and posting descriptions are empty, "
        "so demand is measured by job titles only.",
        "<b>Taxonomy uncertainty.</b> Taxonomy v0.1 is provisional: no legal or media domain, skill parent IDs "
        "inconsistent with domain aliases (public administration), health unresolved. Mappings may change with v0.2.",
    ]:
        S(P("&bull; " + t, BODY))

    S(P("11. Policy statements: allowed and to avoid", H2))
    S(table([["Allowed (cautious, traceable)", "Must avoid in Week 7"],
             ["\"In the Week 3 sample, business and administration is about half of both postings and graduates.\"",
              "\"Uganda has a shortage of supply-chain graduates.\" (2 postings, interval crosses 0)"],
             ["\"The two sampled institutions produce far fewer STEM than humanities graduates (0.11:5).\"",
              "\"Uganda's STEM ratio has fallen below the NDPIV baseline.\""],
             ["\"The sample cannot test the NDPIV ICT-demand statement (para 383); posting descriptions are needed.\"",
              "Any ranking of categories without its denominator, interval and support label"]],
            [8.5 * cm, 8.5 * cm]))

    S(PageBreak())
    S(P("12. Week 7 interface wireframe", H2))
    unc = j[(j.category_id == ex) & (j.status == "in_scope") & (j.mapping_certainty != "certain")].record_id.nunique()
    S(Wireframe(ex={"cid": ex, "label": exr.category_label, "gap": exr.gap_pp, "lo": exr.ci_low_pp,
                    "hi": exr.ci_high_pp, "support": exr.support, "D": exr.demand_share, "S": exr.supply_share,
                    "du": exr.demand_units, "su": exr.supply_graduates, "nd": nd, "ns": ns, "unc": unc,
                    "sha": man["records_sha256"], "tax": man["taxonomy_version"], "eng": man["engine_version"],
                    "data_tag": "Week 3 v0.1.0 working split",
                    "hold": f"{sign_hold(ex)} of {len(scen)} scenarios"}))
    S(P("The card shows the result with its interval and support label, the definition in plain words, the "
        "counts behind both shares, provenance with a link to the record rows, and the limitations that apply to "
        "this category. LOW SUPPORT categories are hidden by default and the not-a-national-estimate banner cannot "
        "be dismissed.", BODY))

    S(P("13. Clean-run instructions", H2))
    for t in ["git checkout feature/week6-gap-engine",
              "pip install pandas numpy pyyaml openpyxl matplotlib reportlab pytest",
              "python src/skillsgap/gap/engine.py          # outputs in data/processed/week6/",
              "python src/skillsgap/gap/export_xlsx.py     # reports/week6/TeamName_Week6_Analysis.xlsx",
              "python src/skillsgap/gap/report_pdf.py      # this report",
              "python -m pytest tests/test_gap_engine.py   # 5 tests, includes a reproducibility check"]:
        S(P(t, MONO))
    S(P("The engine reads the taxonomy from data/raw/taxonomy/ if unpacked, otherwise directly from the Week 4 zip "
        "in the repository root. To re-run on new Week 3 data, point inputs.records in "
        "config/week6/gap_engine.yaml at the new file; unmapped titles appear in "
        "unmatched_uncertain_excluded.csv for new rules.", SMALL))

    def footer(c, d):
        c.saveState()
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor(MUTED))
        c.drawString(2 * cm, 1.2 * cm, "TeamName_Week6_Methodology  |  sample results, not national estimates")
        c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {d.page}")
        c.restoreState()

    out.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(out), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.7 * cm,
                      bottomMargin=1.8 * cm, title="Week 6 Methodology - Gap Analysis",
                      author="Skills-Gap Intelligence Agent team").build(story, onFirstPage=footer,
                                                                         onLaterPages=footer)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--out", default=str(E.REPO_ROOT / "reports" / "week6" / "TeamName_Week6_Methodology.pdf"))
    a = ap.parse_args()
    print(f"Report -> {build(E.run(a.config), Path(a.out))}")
