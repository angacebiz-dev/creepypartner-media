import json,sys,urllib.request,urllib.parse,os
from PIL import Image,ImageDraw
out=[]
for q in sys.argv[2:]:
    u="https://images-api.nasa.gov/search?media_type=image&q="+urllib.parse.quote(q)
    d=json.load(urllib.request.urlopen(u,timeout=30))
    for x in d['collection']['items'][:8]:
        m=x['data'][0];nid=m['nasa_id']
        if any(o['id']==nid for o in out): continue
        out.append({'id':nid,'q':q,'title':m['title'],'center':m.get('center'),'desc':(m.get('description') or '')[:300],'thumb':x['links'][0]['href'] if x.get('links') else None})
tag=sys.argv[1]; json.dump(out,open(f'cand_{tag}.json','w'),indent=1)
W=200;cols=8;rows=(len(out)+cols-1)//cols;sheet=Image.new('RGB',(W*cols,(W+20)*rows));d=ImageDraw.Draw(sheet)
for i,o in enumerate(out):
    try:
        p=f"t_{o['id']}.jpg";urllib.request.urlretrieve(o['thumb'],p);im=Image.open(p).convert('RGB');im.thumbnail((W,W))
        sheet.paste(im,((i%cols)*W,(i//cols)*(W+20)))
    except Exception as e: pass
    d.text(((i%cols)*W+3,(i//cols)*(W+20)+W+3),str(i),fill=(255,255,0))
sheet.save(f'sheet_{tag}.jpg')
for i,o in enumerate(out): print(i,o['id'],'|',o['title'][:60])
