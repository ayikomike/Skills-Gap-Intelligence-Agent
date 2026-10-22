"""Demand-side parsers (job postings). Parsers are pure functions of HTML -> records,
so they can be unit-tested on saved pages and re-run from cache without hitting the site."""
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .schema import estimate_posted_date, make_record

log = logging.getLogger("skillsgap.demand")
_POSTED = re.compile(r"^(today|yesterday|\d+\s+(day|week|month|year)s?\s+ago)$", re.I)
_AGE = re.compile(r"\b(today|yesterday|\d+\s+(?:day|week|month|year)s?\s+ago)\b", re.I)


def parse_brightermonday_listing(html, page_url, retrieved_at, method="http_get"):
    """Parse a BrighterMonday results page. Strategy: every <a href*='/listings/'> is a
    posting; the card text around it supplies employer, location, posted age, job function.
    Returns (records, failures). Selectors are deliberately structure-light because the
    live markup must be validated on the first live run (see docs/DATA_QUALITY_MEMO)."""
    soup = BeautifulSoup(html, "lxml")
    records, failures, seen = [], [], set()
    for a in soup.select("a[href*='/listings/']"):
        href = urljoin(page_url, a.get("href", ""))
        title = a.get_text(" ", strip=True)
        if not title or href in seen:
            continue
        seen.add(href)
        card = a
        for _ in range(4):  # climb to the enclosing card, but never into a container
            par = card.parent  # that holds more than one distinct listing (would mix postings)
            if par is None:
                break
            hrefs = {urljoin(page_url, x.get("href", "")) for x in par.select("a[href*='/listings/']")}
            if len(hrefs) > 1:
                break
            card = par
            if len(card.get_text(" ", strip=True)) > len(title) + 20:
                break
        lines = [s.strip() for s in card.get_text("\n", strip=True).split("\n") if s.strip()]
        lines = [l for l in lines if l != title]
        posted = next((l for l in lines if _POSTED.match(l)), "")
        func = next((re.sub(r"^Job Function\s*:\s*", "", l, flags=re.I)
                     for l in lines if l.lower().startswith("job function")), "")
        rest = [l for l in lines if l != posted and not l.lower().startswith("job function")]
        employer = rest[0] if rest else ""
        location = rest[1] if len(rest) > 1 else ""
        employment_type, salary_text = "", ""
        # Structured layout seen on the live page: employer = blue <p> outside the title link;
        # chips = <span class="rounded"> (location, employment type, salary); function = grey <p>.
        emp_p = next((p for p in card.find_all("p") if p.find_parent("a") is None
                      and "text-blue-700" in (p.get("class") or [])), None)
        chips = [s.get_text(" ", strip=True) for s in card.select("span.rounded")]
        if emp_p is not None and chips:
            employer = emp_p.get_text(" ", strip=True)
            loc_set = False
            for c in chips:
                if re.search(r"full.?time|part.?time|contract|intern|temporary|volunteer|freelance", c, re.I):
                    employment_type = employment_type or c
                elif re.search(r"\bUSh\b|\bUGX\b", c):
                    salary_text = salary_text or c
                elif not loc_set:
                    location, loc_set = c, True
            fn_p = card.select_one("p.text-gray-500")
            if fn_p is not None:
                func = fn_p.get_text(" ", strip=True)
        if not posted:  # on the live page the age is a sibling <p> OUTSIDE the inner card:
            outer = a       # climb to the largest container that still holds only this listing
            for _ in range(8):
                par = outer.parent
                if par is None:
                    break
                if len({urljoin(page_url, x.get("href", "")) for x in par.select("a[href*='/listings/']")}) > 1:
                    break
                outer = par
            for p_tag in outer.find_all("p"):
                t_age = p_tag.get_text(" ", strip=True)
                if _POSTED.match(t_age):
                    posted = t_age
                    break
        if not posted:  # relative age may sit inside a longer text such as "Posted 4 days ago"
            m_age = _AGE.search(card.get_text(" ", strip=True))
            posted = m_age.group(0) if m_age else ""
        if not employer:
            failures.append({"url": href, "reason": "employer_not_found"})
        records.append(make_record(
            "demand", "brightermonday", page_url, retrieved_at, method,
            id_parts=[href], raw_for_hash=card.get_text(" ", strip=True),
            record_url=href, title=title, employer=employer, location=location,
            posted_text=posted, posted_date_est=estimate_posted_date(posted, retrieved_at),
            function_raw=func, employment_type=employment_type, salary_text=salary_text))
    if not records:
        failures.append({"url": page_url, "reason": "no_listing_links_found"})
    return records, failures


def parse_district_advert(html, page_url, retrieved_at, source="district_adverts", method="http_get"):
    """Parse a district service commission advert page: a table of posts + a deadline sentence."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    m = re.search(r"not later than\s+([^.,;]+?\d{4})", text, re.I)
    deadline = m.group(1).strip() if m else ""
    records, failures = [], []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        head = [c.get_text(" ", strip=True).lower() for c in rows[0].find_all(["th", "td"])]
        idx = {k: next((i for i, h in enumerate(head) if k in h), None)
               for k in ("department", "job title", "ref", "salary", "vacanc")}
        if idx["job title"] is None:
            continue
        for r in rows[1:]:
            c = [x.get_text(" ", strip=True) for x in r.find_all(["td", "th"])]
            if len(c) <= idx["job title"] or not c[idx["job title"]]:
                failures.append({"url": page_url, "reason": "row_without_title"})
                continue
            g = lambda k: c[idx[k]] if idx[k] is not None and idx[k] < len(c) else ""
            records.append(make_record(
                "demand", source, page_url, retrieved_at, method,
                id_parts=[page_url, g("ref"), g("job title")], raw_for_hash=" ".join(c),
                record_url=page_url, title=g("job title"), employer=_host_label(page_url),
                department=g("department"), ref_no=g("ref"), salary_scale=g("salary"),
                vacancies=g("vacanc"), deadline=deadline, function_raw=g("department")))
    if not records:  # advert typed as tab-separated text lines (br-separated), not an HTML table
        row_re = re.compile(r"^\s*\d+\.?\s*(.+?)\s+([A-Z0-9]+(?:/[A-Z0-9]+)+)\s+(.+?)\s+(U\d+[A-Z]?)\s+(\d+)\s*$")
        for ln in soup.get_text("\n").splitlines():
            m = row_re.match(ln.replace("\xa0", " "))
            if not m:
                continue
            dept, ref, title, scale, vac = [re.sub(r"\s+", " ", x).strip() for x in m.groups()]
            records.append(make_record(
                "demand", source, page_url, retrieved_at, method,
                id_parts=[page_url, ref, title], raw_for_hash=ln,
                record_url=page_url, title=title, employer=_host_label(page_url),
                department=dept, ref_no=ref, salary_scale=scale, vacancies=vac,
                deadline=deadline, function_raw=dept))
    if not records:
        failures.append({"url": page_url, "reason": "no_vacancy_table_found"})
    return records, failures


def _host_label(url):
    from urllib.parse import urlparse
    return urlparse(url).netloc
