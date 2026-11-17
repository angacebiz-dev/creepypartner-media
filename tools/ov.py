"""Openverse search + download (Flickr / Wikimedia / museums), writes credits.json like fetch.py.
  python3 ov.py search "<query>" [n]            -> prints index, source, license, creator, size, title, url
  python3 ov.py get <out_dir> <name> <id-or-url> [creator] [license] [src]
  python3 ov.py getid <out_dir> <name> <openverse id>
Downloads go to <out_dir>/<name>; credits.json gets {artist, license, src}.
"""
import json, os, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "CreepyPartnerVideoTool/1.0 (https://github.com/angacebiz-dev/creepypartner-media)"}
API = "https://api.openverse.org/v1/images/"
SRC = {"flickr": "Flickr", "wikimedia": "Wikimedia Commons", "smithsonian_american_art_museum": "Smithsonian",
       "nypl": "NYPL", "library_of_congress": "Library of Congress", "met": "The Met", "rawpixel": "rawpixel"}
LIC = {"pdm": "Public domain", "cc0": "CC0", "by": "CC BY", "by-sa": "CC BY-SA", "by-nc": "CC BY-NC",
       "by-nc-sa": "CC BY-NC-SA", "by-nd": "CC BY-ND", "by-nc-nd": "CC BY-NC-ND"}


def jget(url):
    for i in range(5):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (i + 1)); continue
            raise


def search(q, n=20, extra=""):
    d = jget(API + "?" + urllib.parse.urlencode({"q": q, "page_size": n}) + extra)
    for i, r in enumerate(d["results"]):
        print(f"{i:2d} {r['id']} {r['source'][:10]:10s} {r['license']:8s} {str(r.get('width'))+'x'+str(r.get('height')):10s} "
              f"{(r.get('creator') or '?')[:22]:22s} | {r['title'][:60]} | {r['url']}")
    return d["results"]


def download(url, out):
    for i in range(6):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
            open(out, "wb").write(data); return len(data)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(20 * (i + 1)); continue
            raise


def save(out_dir, name, url, creator, lic, src):
    os.makedirs(out_dir, exist_ok=True)
    n = download(url, os.path.join(out_dir, name))
    cf = os.path.join(out_dir, "credits.json")
    cr = json.load(open(cf)) if os.path.exists(cf) else {}
    cr[name] = {"artist": creator or "Unknown", "license": lic, "src": src, "url": url}
    json.dump(cr, open(cf, "w"), indent=1)
    print("saved", name, n, creator, lic, src)


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "search":
        search(a[2], int(a[3]) if len(a) > 3 else 20)
    elif a[1] == "getid":
        r = jget(API + a[4] + "/")
        save(a[2], a[3], r["url"], r.get("creator"), LIC.get(r["license"], r["license"].upper()), SRC.get(r["source"], r["source"].title()))
    elif a[1] == "get":
        save(a[2], a[3], a[4], a[5] if len(a) > 5 else "Unknown", a[6] if len(a) > 6 else "?", a[7] if len(a) > 7 else "?")
