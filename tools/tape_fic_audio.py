import json, numpy as np, soundfile as sf, subprocess
from kokoro_onnx import Kokoro
from scipy.signal import butter, sosfilt, resample_poly
k=Kokoro('/home/claude/tts/kokoro-v1.0.onnx','/home/claude/tts/voices-v1.0.bin')
SR=44100; rng=np.random.default_rng(11)
def bp(x,lo,hi,o=4): return sosfilt(butter(o,[lo,hi],btype='band',fs=SR,output='sos'),x)
def tts(text,voice,speed):
    s,sr=k.create(text,voice=voice,speed=speed,lang='en-us'); s=resample_poly(s,SR,sr)
    nz=np.where(np.abs(s)>0.01)[0]; return s[max(0,nz[0]-400):nz[-1]+800]
def phone(x,gain=1.0,soft=False):
    y=bp(x,320,3300); y=np.tanh(y*(2.2 if not soft else 1.4))*gain; return y
# (speaker, text, voice, speed, gap_before, soft, gain)
L=[("DISPATCH","911, what's the address of your emergency?","af_sarah",1.0,0.3,False,0.55),
("CALLER","Fourteen Alder Lane. Please... someone's in my house.","af_nicole",0.9,0.5,True,0.9),
("DISPATCH","Okay, ma'am. Are you somewhere safe right now?","af_sarah",1.0,0.35,False,0.55),
("CALLER","I'm in the closet. Upstairs. He... he used a key.","af_nicole",0.88,0.4,True,0.9),
("DISPATCH","Who else has a key to your house?","af_sarah",1.0,0.35,False,0.55),
("CALLER","Only my husband.","af_nicole",0.88,0.5,True,0.9),
("DISPATCH","Is your husband home with you tonight?","af_sarah",1.0,0.35,False,0.55),
("CALLER","My husband went missing three years ago.","af_nicole",0.85,1.1,True,0.9),
("CALLER","Do you hear that? He's whistling. That's his song... he always whistled it when he came home.","af_nicole",0.88,3.6,True,0.9),
("DISPATCH","Ma'am, officers are on the way. Stay on the line with me.","af_sarah",1.0,0.4,False,0.55),
("CALLER","He's on the stairs.","af_nicole",0.85,0.6,True,0.9),
("CALLER","He stopped. He's right outside the door.","af_nicole",0.82,3.4,True,0.8),
("DISPATCH","Ma'am? Ma'am, can you hear me?","af_sarah",1.0,0.6,False,0.55),
("UNKNOWN","Hi, honey.","am_onyx",0.72,1.6,False,0.6)]
t=0.5; segs=[]; subs=[]; marks={}
for i,(spk,txt,v,sp,gap,soft,g) in enumerate(L):
    t+=gap; s=tts(txt,v,sp)
    if spk=="UNKNOWN":
        s=resample_poly(s,119,100)
        subprocess.run(["true"])
    y=phone(s,g,soft); segs.append((t,y)); d=len(y)/SR
    subs.append({"t0":round(t-0.05,2),"t1":round(t+d+0.25,2),"spk":spk,"text":txt}); marks[i]=(t,t+d); t+=d
end_dialogue=t
# Unknown voice: pitch down 3 semitones via sox-like resample (ffmpeg later is simpler) - done by placing processed copy
total_dlg=t+0.4
n=int(SR*(total_dlg+12)); a=np.zeros(n)
for t0,y in segs:
    i=int(t0*SR); a[i:i+len(y)]+=y
# line static/hum during call
st=bp(rng.standard_normal(n),300,3400,2)*0.018; hum=0.006*np.sin(2*np.pi*60*np.arange(n)/SR)
callmask=(np.arange(n)/SR<total_dlg).astype(float); a+=(st+hum)*callmask
# whistle: original 6-note phrase in the gap before line 8
w0=marks[7][1]+0.4; notes=[(659,0.42),(587,0.28),(523,0.55),(587,0.3),(494,0.75),(440,0.9)]
tt=w0
for f,du in notes:
    m=int(du*SR); x=np.arange(m)/SR; vib=1+0.012*np.sin(2*np.pi*5.5*x)
    ph=2*np.pi*np.cumsum(f*vib)/SR; env=np.minimum(1,x/0.04)*np.minimum(1,(du-x)/0.06)
    wv=(np.sin(ph)+0.15*rng.standard_normal(m)*0.3)*env*0.05
    i=int(tt*SR); a[i:i+m]+=bp(wv,320,3300,2)*1.0; tt+=du+0.05
# footsteps between "on the stairs" and "stopped"
f0=marks[10][1]+0.5
for j in range(6):
    i=int((f0+j*0.5)*SR); m=int(0.18*SR); x=np.arange(m)/SR
    th=(np.sin(2*np.pi*70*x)+0.5*rng.standard_normal(m))*np.exp(-x/0.035)*(0.18+0.05*j)
    a[i:i+m]+=bp(th,320,3300,2)*3
# creak
ci=int((f0+3.0)*SR); m=int(0.5*SR); x=np.arange(m)/SR
cr=np.sign(np.sin(2*np.pi*(180+90*np.sin(2*np.pi*3*x))*x))*np.exp(-((x-0.25)/0.15)**2)*0.05; a[ci:ci+m]+=bp(cr,320,3300,2)
# hang-up click + disconnect tones
h=int(total_dlg*SR); a[h:h+300]+=0.6*np.hanning(300)
x=np.arange(int(0.28*SR))/SR
for q,f in enumerate([913.8,1370.6,1776.7]):
    i=h+int((0.6+q*0.3)*SR); a[i:i+len(x)]+=0.12*np.sin(2*np.pi*f*x)
sf.write('dlg_raw.wav',np.stack([a,a],1).astype(np.float32),SR)
json.dump({"subs":subs,"end":total_dlg,"unk":marks[13]},open('t.json','w'))
print(total_dlg, marks[13])
