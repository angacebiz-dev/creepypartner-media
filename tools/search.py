import json, os, sys, time, urllib.parse
sys.path.insert(0, "/home/claude/partner")
from fetch import get, API
out = sys.argv[1]; qs = sys.argv[2:]
res = json.load(open(out)) if os.path.exists(out) else {}
for q in qs:
    if q in res: continue
    p = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": q, "srnamespace": 6, "srlimit": 25, "format": "json"})
    try:
        res[q] = [r["title"] for r in get(API + p)["query"]["search"]]; print("ok", q, len(res[q]), flush=True)
    except Exception as e:
        print("fail", q, e, flush=True)
    json.dump(res, open(out, "w"), indent=1)
