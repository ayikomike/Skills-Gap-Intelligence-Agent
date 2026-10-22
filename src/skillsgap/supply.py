"""Supply-side parser: published university graduation lists (PDF) -> programme-level counts.

PRIVACY BY DESIGN: graduate names, registration numbers, gender and nationality columns are
counted but NEVER stored. Only (institution, ceremony, award level, programme, count) leaves
this module.
"""
import io
import logging
import re

from .schema import make_record

log = logging.getLogger("skillsgap.supply")

AWARD = re.compile(r"\b(bachelor|master|doctor|ph\.?d|post\s?graduate|pgd|diploma|certificate)\b", re.I)
ROW = re.compile(r"^\s*(\d{1,4})[.)]?\s+[A-Za-z]")
SERIAL_JUMP = 60   # largest forward gap in serial numbers we still treat as the same list

_LEVELS = [("ph", "PhD"), ("doctor", "PhD"), ("master", "Masters"), ("post", "Postgraduate diploma"),
           ("pgd", "Postgraduate diploma"), ("bachelor", "Bachelors"), ("diploma", "Diploma"),
           ("certificate", "Certificate")]

_NON_STEM = re.compile(r"business|management|administration|secretarial|education|law|arts|social|"
                       r"journalism|communication|theolog|islamic|shari|human resource|procurement|"
                       r"logistics|finance|banking|public policy|governance|accounting|marketing|"
                       r"monitoring|project planning|library", re.I)
_STEM = re.compile(r"computer|information (technology|systems)|software|engineering|statistics|"
                   r"mathematic|physics|chemistry|biolog|agricultur|environmental science|"
                   r"information security|data|\bscience\b", re.I)
_REVIEW = re.compile(r"medicine|surgery|nursing|biomedical|public health|health|pharmac|dental", re.I)


def classify_level(heading):
    h = heading.lower()
    for key, label in _LEVELS:
        if re.search(r"\b" + re.escape(key), h):
            return label
    return "Other"


def classify_field(programme):
    """PROVISIONAL grouping for the NDPIV STEM:humanities comparison. Health programmes are
    flagged REVIEW because the supervisor must confirm whether NDPIV counts them as STEM."""
    if _REVIEW.search(programme):
        return "REVIEW_HEALTH"
    if _NON_STEM.search(programme) and not re.search(r"computer|information (technology|systems)|engineering", programme, re.I):
        return "NON_STEM"
    if _STEM.search(programme):
        return "STEM"
    return "NON_STEM"


def extract_pdf_lines(data):
    import pdfplumber
    lines = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            lines.extend(txt.splitlines())
    return lines


def count_confidence(count, matched):
    """How far the serial-based count is from the rows we could actually read."""
    ratio = count / matched if matched else 99
    return "high" if ratio <= 1.15 else ("medium" if ratio <= 1.6 else "low")


def clean_heading(text):
    """Drop OCR junk at the end of a heading (e.g. ".'qt('" or a stray single lowercase letter)."""
    toks = text.split()
    while toks and (not re.fullmatch(r"[A-Za-z()&,/-]+", toks[-1]) or (len(toks[-1]) == 1 and toks[-1].islower())):
        toks.pop()
    return " ".join(toks)


def count_programmes(lines):
    """Walk lines; an award-like heading starts a bucket; numbered rows increment it.
    Each bucket is [heading, rows_matched, highest_serial]. The highest serial number is the
    better count, because scanned (OCR) lists lose some rows but keep the final serial.
    Returns buckets and the number of numbered rows seen before any heading."""
    buckets, current, orphan_rows = [], None, 0
    for line in lines:
        s = line.strip()
        if not s:
            continue
        m = ROW.match(s)
        if m:
            if current is None:
                orphan_rows += 1
            else:
                current[1] += 1
                n = int(m.group(1))
                # accept a serial only if it moves forward by at most SERIAL_JUMP: ignores stray numbers
                # (years, page numbers, phone digits) but tolerates whole pages of unreadable rows
                if current[2] < n <= current[2] + SERIAL_JUMP:
                    current[2] = n
            continue
        if AWARD.search(s) and len(s) < 140 and not re.search(r"\d{4}", s[:4]):
            h = clean_heading(s)
            if h and (current is None or current[1] > 0 or current[0] != h):
                current = [h, 0, 0]
                buckets.append(current)
    return [tuple(b) for b in buckets], orphan_rows


def parse_graduation_pdf(data, meta, retrieved_at, method="http_get"):
    lines = extract_pdf_lines(data)
    buckets, orphan = count_programmes(lines)
    records, failures = [], []
    for heading, matched, top in buckets:
        if matched == 0:
            failures.append({"url": meta["url"], "reason": f"heading_without_numbered_rows: {heading[:60]}"})
            continue
        records.append(make_record(
            "supply", meta["name"], meta["url"], retrieved_at, method,
            id_parts=[meta["url"], heading], raw_for_hash=f"{heading}|{top}", record_url=meta["url"],
            institution=meta["institution"], ceremony=meta["ceremony"],
            award_level=classify_level(heading), programme=heading, graduate_count=max(top, matched),
            count_basis="last_valid_serial_number", rows_matched=matched,
            count_confidence=count_confidence(max(top, matched), matched),
            field_group_provisional=classify_field(heading)))
    if orphan:
        failures.append({"url": meta["url"], "reason": f"{orphan} numbered rows before any heading"})
    if not records:
        failures.append({"url": meta["url"], "reason": "no_programme_buckets_parsed (list may be unnumbered or scanned: needs OCR or a custom rule)"})
    return records, failures
