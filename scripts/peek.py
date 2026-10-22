import base64, json, glob, io, re
import pdfplumber
AWARD = re.compile(r"\b(bachelor|master|doctor|ph\.?d|post\s?graduate|pgd|diploma|certificate)\b", re.I)
def shape(l):
    return "  . " + " ".join("N" if t.isdigit() else ("W" if t.isalpha() else "X") for t in l.split()[:12])
def show(lines, n):
    for l in lines[:n]:
        print(l if AWARD.search(l) else shape(l))   # names are never printed, only their shape
for f in glob.glob("cache/*.json"):
    d = json.load(open(f, encoding="utf-8")); u = d["url"]; body = base64.b64decode(d["body_b64"])
    if "brightermonday" in u and u.endswith("/jobs"):
        h = body.decode("utf-8", "replace"); i = h.find("/listings/")
        print("=== BM CARD HTML ==="); print(h[max(0, i-800):i+1800])
    elif "lyantonde" in u:
        h = body.decode("utf-8", "replace"); i = h.find("Education Officer")
        print("=== LYANTONDE HTML ==="); print(h[max(0, i-1500):i+1500])
    elif u.endswith("Grad-List-2025.pdf") or u.endswith("kc.pdf"):
        with pdfplumber.open(io.BytesIO(body)) as pdf:
            p = pdf.pages[1]; lines = (p.extract_text() or "").splitlines()
            print("=== PDF", u.split("/")[-1], "pages:", len(pdf.pages), "(page 2 shape) ===")
            show(lines, 45)
