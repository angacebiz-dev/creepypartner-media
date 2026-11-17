# usage: chk.sh <video> <out.jpg>  -> 14-frame contact sheet
v=$1; d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v"); echo "dur $d"
rm -f /tmp/ck_*.jpg
python3 - "$v" "$d" "$2" <<'P'
import sys,subprocess
from PIL import Image
v,d,out=sys.argv[1],float(sys.argv[2]),sys.argv[3]
ts=[0.2,2.5]+[4+i*(d-8)/11 for i in range(12)]
S=Image.new('RGB',(180*7,320*2))
for i,t in enumerate(ts):
    f=f'/tmp/ck_{i}.jpg'; subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',v,'-frames:v','1','-vf','scale=180:320',f])
    S.paste(Image.open(f),((i%7)*180,(i//7)*320))
S.save(out)
P
