"""Commons thumbnail download (API-free). python3 cmt.py <out_dir> <name> "<File title>" <width> <artist> <license>"""
import hashlib, sys, urllib.parse, json, os, urllib.request
d, name, title, width, artist, lic = sys.argv[1:7]
fn = title.replace("File:", "").replace(" ", "_"); h = hashlib.md5(fn.encode()).hexdigest()
q = urllib.parse.quote(fn)
url = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{width}px-{q}" + (".png" if fn.lower().endswith((".svg", ".tif", ".tiff")) else "")
os.makedirs(d, exist_ok=True)
data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "CreepyPartnerVideoTool/1.0 (https://github.com/angacebiz-dev/creepypartner-media)"}), timeout=60).read()
open(os.path.join(d, name), "wb").write(data)
cf = os.path.join(d, "credits.json"); c = json.load(open(cf)) if os.path.exists(cf) else {}
c[name] = {"artist": artist, "license": lic, "src": "Wikimedia Commons", "url": url}; json.dump(c, open(cf, "w"), indent=1)
print("saved", name, len(data))
