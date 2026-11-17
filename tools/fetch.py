"""Slow, polite Wikimedia Commons fetcher (one request at a time, backoff on 429).
Usage:
  python3 fetch.py cats  <out.json> "Category A" "Category B" ...   -> lists file titles per category
  python3 fetch.py files <jobs.txt>                                 -> jobs: one per line "<title>|<out path>"
Credits for downloaded files are appended to <dir of out path>/credits.json."""
import json, os, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "CreepyPartnerVideoTool/1.0 (https://github.com/angacebiz-dev)"}
API = "https://commons.wikimedia.org/w/api.php?"
GAP = 9


def get(url, binary=False, tries=7):
    wait = 30
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90)
            d = r.read()
            time.sleep(GAP)
            return d if binary else json.loads(d)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                ra = e.headers.get("retry-after")
                w = int(ra) if ra and ra.isdigit() else wait
                print(f"   {e.code}, waiting {w}s", flush=True)
                time.sleep(w); wait = min(wait * 2, 300)
                continue
            raise
        except Exception as e:
            print("   err", e, flush=True); time.sleep(wait); wait = min(wait * 2, 300)
    raise RuntimeError("gave up " + url[:80])


def strip(h):
    return re.sub(r"<[^>]+>", "", h or "").strip()


def info(title):
    q = urllib.parse.urlencode({"action": "query", "titles": title, "prop": "imageinfo",
                                "iiprop": "url|extmetadata|size|mime", "format": "json"})
    d = get(API + q)
    p = next(iter(d["query"]["pages"].values()))
    ii = p["imageinfo"][0]; em = ii.get("extmetadata", {})
    return {"title": title, "url": ii["url"], "w": ii.get("width"), "h": ii.get("height"), "mime": ii.get("mime"),
            "size": ii.get("size"), "artist": strip(em.get("Artist", {}).get("value"))[:80],
            "license": strip(em.get("LicenseShortName", {}).get("value")),
            "desc": strip(em.get("ImageDescription", {}).get("value"))[:300]}


def cats(out, names):
    res = {}
    if os.path.exists(out):
        res = json.load(open(out))
    for c in names:
        if c in res:
            continue
        q = urllib.parse.urlencode({"action": "query", "list": "categorymembers", "cmtitle": "Category:" + c,
                                    "cmtype": "file|subcat", "cmlimit": 100, "format": "json"})
        try:
            res[c] = [m["title"] for m in get(API + q)["query"]["categorymembers"]]
            print("cat", c, len(res[c]), flush=True)
        except Exception as e:
            print("cat fail", c, e, flush=True)
        json.dump(res, open(out, "w"), indent=1)


def files(jobs):
    for line in open(jobs):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        title, out = line.split("|")
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        cf = os.path.join(os.path.dirname(out), "credits.json")
        cr = json.load(open(cf)) if os.path.exists(cf) else {}
        try:
            m = info(title)
            if m["size"] and m["size"] > 25_000_000:
                print("skip too big", title, m["size"], flush=True); continue
            data = get(m["url"], binary=True)
            open(out, "wb").write(data)
            cr[os.path.basename(out)] = m
            json.dump(cr, open(cf, "w"), indent=1)
            print("ok", out, len(data), m["license"], flush=True)
        except Exception as e:
            print("FAIL", title, e, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "cats":
        cats(sys.argv[2], sys.argv[3:])
    else:
        files(sys.argv[2])
