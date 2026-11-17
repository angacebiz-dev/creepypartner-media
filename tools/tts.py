import sys, json, numpy as np, soundfile as sf, subprocess
from kokoro_onnx import Kokoro
k = Kokoro('/home/claude/tts/kokoro-v1.0.onnx', '/home/claude/tts/voices-v1.0.bin')

def creepy(inp, out, semis=-2.0, tempo=0.97):
    r = 2 ** (semis / 12)
    af = (f"asetrate=24000*{r:.4f},aresample=24000,atempo={tempo/r:.4f},"
          "highpass=f=60,lowpass=f=9000,"
          "aecho=0.85:0.5:35|70:0.18|0.10,"
          "acompressor=threshold=-20dB:ratio=3:attack=5:release=120,volume=1.3")
    subprocess.run(["ffmpeg","-loglevel","error","-y","-i",inp,"-af",af,"-ar","44100",out],check=True)

if len(sys.argv) > 1 and sys.argv[1] == "sampler":
    line = "If you drive Route 9 after midnight... there are rules."
    parts = []
    for i, v in enumerate(["am_onyx", "am_fenrir", "bm_lewis", "am_michael"], 1):
        s, sr = k.create(f"Option {i}. {line}", voice=v, speed=0.88, lang="en-us")
        sf.write(f"raw_{v}.wav", s, sr); creepy(f"raw_{v}.wav", f"cr_{v}.wav"); parts.append(f"cr_{v}.wav")
    with open("samp.txt","w") as f: f.writelines(f"file '{p}'\nfile 'gap.wav'\n" for p in parts)
    subprocess.run(["ffmpeg","-loglevel","error","-y","-f","lavfi","-i","anullsrc=r=44100:cl=mono","-t","0.8","gap.wav"],check=True)
    subprocess.run(["ffmpeg","-loglevel","error","-y","-f","concat","-safe","0","-i","samp.txt","-c:a","libmp3lame","-b:a","160k","Partner_voice_options.mp3"],check=True)
    print("sampler done")
