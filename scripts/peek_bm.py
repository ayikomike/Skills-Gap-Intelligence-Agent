"""Print the HTML of ONE real BrighterMonday job card (from the cache) so the parser can be fixed.
Run from the repo root after a pipeline run:  python scripts/peek_bm.py > out/peek_bm.txt"""
import base64, glob, json
from bs4 import BeautifulSoup

for f in glob.glob("cache/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    if "brightermonday" in d["url"] and d["url"].endswith("/jobs"):
        soup = BeautifulSoup(base64.b64decode(d["body_b64"]).decode("utf-8", "replace"), "lxml")
        for t in soup(["script", "style", "svg", "noscript"]):
            t.decompose()
        a = soup.body.select_one("a[href*='/listings/']")
        card = a
        for _ in range(4):
            if card.parent is not None and len(card.parent.select("a[href*='/listings/']")) <= 2:
                card = card.parent
        print("anchors with /listings/ in body:", len(soup.body.select("a[href*='/listings/']")))
        print(card.prettify()[:4500])
        break
else:
    print("BrighterMonday page not found in cache/: run the pipeline first")
