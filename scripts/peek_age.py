import base64, glob, json, re
for f in glob.glob("cache/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    if "brightermonday" in d["url"]:
        t = base64.b64decode(d["body_b64"]).decode("utf-8", "replace")
        print(d["url"], "| 'ago' count:", len(re.findall(r"\bago\b", t)))
        for m in re.findall(r".{80}\bago\b.{20}", t, re.S)[:3]:
            print("   ", m.replace("\n", " "))
