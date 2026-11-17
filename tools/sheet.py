import sys,glob,os
from PIL import Image, ImageDraw
fs=sorted(f for f in glob.glob(sys.argv[1]+"/*") if f.lower().endswith(('.jpg','.png','.jpeg','.gif','.webp')) and '_' not in os.path.basename(f))
cols=5; tw,th=300,220; S=Image.new("RGB",(cols*tw,((len(fs)+cols-1)//cols)*(th+20)),(30,30,30)); d=ImageDraw.Draw(S)
for i,f in enumerate(fs):
    try:
        im=Image.open(f).convert("RGB"); im.thumbnail((tw-6,th-6)); x,y=(i%cols)*tw,(i//cols)*(th+20)
        S.paste(im,(x+3,y+3)); d.text((x+4,y+th+2),os.path.basename(f)+f" {Image.open(f).size}",fill=(255,255,0))
    except Exception as e: print(f,e)
S.save(sys.argv[2]); print(len(fs))
