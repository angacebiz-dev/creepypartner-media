import sys, json, time, urllib.parse
sys.path.insert(0,'/home/claude/creepypartner-media/tools')
import ov
Q=json.load(open(sys.argv[1])); out='/home/claude/partner/wk/tapes/img2'
for name,q in Q.items():
    for attempt in range(3):
        try:
            d=ov.jget(ov.API+"?"+urllib.parse.urlencode({"q":q,"page_size":12})+"&license=by,by-sa,cc0,pdm,by-nc,by-nc-sa&source=flickr")
            break
        except Exception as e:
            print('retry',name,e); time.sleep(8); d={"results":[]}
    rs=[r for r in d["results"] if (r.get('width') or 0)>=800][:3]
    for i,r in enumerate(rs):
        try:
            ov.save(out,f"{name}_{i}.jpg",r['url'],r.get('creator') or '?',ov.LIC.get(r['license'],r['license']),ov.SRC.get(r['source'],r['source']))
        except Exception as e: print('fail',name,i,e)
    print(name,len(rs),flush=True)
