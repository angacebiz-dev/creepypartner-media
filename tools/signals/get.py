import json,sys,urllib.request,urllib.parse,os,re
from PIL import Image
tag=sys.argv[1]; idx=[int(x) for x in sys.argv[2].split(',')]; c=json.load(open(f'cand_{tag}.json'))
cr=json.load(open('credits.json')) if os.path.exists('credits.json') else {}
for i in idx:
    nid=c[i]['id']; fn=f"{tag}_{i}.jpg"
    if not os.path.exists(fn):
        m=json.load(urllib.request.urlopen(f"https://images-api.nasa.gov/asset/{urllib.parse.quote(nid)}",timeout=30))
        hs=[x['href'] for x in m['collection']['items'] if re.search(r'\.(jpe?g|png|tif)$',x['href'],re.I)]
        pref=[h for k in ['~large','~orig','~medium','~small'] for h in hs if k in h and not h.lower().endswith('tif')]
        for h in pref:
            try:
                urllib.request.urlretrieve(h.replace('http://','https://').replace(' ','%20'),fn); im=Image.open(fn); im.load()
                if max(im.size)>2600: im.thumbnail((2600,2600))
                im.convert('RGB').save(fn,quality=92); break
            except Exception as e: print('x',h,e)
    ctr={'JPL':'NASA/JPL-Caltech','GSFC':'NASA Goddard','JSC':'NASA JSC','HQ':'NASA HQ','KSC':'NASA KSC','ARC':'NASA Ames'}.get(c[i]['center'] or '', 'NASA')
    cr[fn]={'text':f"Photo: {ctr} ({nid}) / public domain / images.nasa.gov"}
    print(fn, Image.open(fn).size, c[i]['title'][:50])
json.dump(cr,open('credits.json','w'),indent=1)
