# Creepy Partner build tools

Rebuild a working setup in a fresh session:

```bash
pip install --break-system-packages kokoro-onnx soundfile scipy numpy pillow
mkdir -p /home/claude/tts /home/claude/partner/fonts /home/claude/partner/video02 /home/claude/partner/wk
# Kokoro model files (GitHub releases, thewh1teagle/kokoro-onnx, tag model-files-v1.0)
curl -L -o /home/claude/tts/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -o /home/claude/tts/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cp tools/fonts/*.ttf /home/claude/partner/fonts/
cp tools/assets/*.png /home/claude/partner/
cp tools/tts.py /home/claude/partner/video02/
cp tools/doc.py tools/car2.py tools/endcard.py tools/cover.py tools/fetch.py tools/search.py /home/claude/partner/
cp -r tools/specs/* /home/claude/partner/wk/
```

| Script | What it does |
|---|---|
| `doc.py spec.json` | Partner Files documentary short: Kokoro voice (bm_lewis, creepy pitch-down), puppet-jaw Partner for hook + end lines, real photos/clips with slow pans and small credits, ASS captions (Anton, active word yellow), synthesized creepy bed, 0.5 s cover flash, 3.2 s comment/follow end card. Outputs `CreepyPartner_<id>.mp4`, a ~2.78 MB 720p `light_<id>.mp4` (Drive route) and `sheet.png` (check frames). |
| `car2.py spec.json --video` | 10-slide story carousel (1080x1920 JPGs, last slide = comment ritual + follow) and, with `--video`, a swipe-style slideshow video with creepy music (all carousels go out as slideshow videos: Lodo wants creepy music, never silent, never TikTok auto-music). |
| `endcard.py "COMMENT ..." out.mp4` | 3.2 s end card: Partner face, yellow comment ritual, FOLLOW CREEPY PARTNER, TikTok / YouTube / @creepypartner (names as text, no logos). |
| `cover.py` | `make_cover(src, title, out, sub, focus_y)` designed cover frame. |
| `fetch.py` | Polite Wikimedia Commons downloader (`cats` / `files jobs.txt`), writes credits.json per folder. |
| `search.py` | Commons file search to JSON. |
| `ov.py` | Openverse search/download (Flickr, Commons, museums) with credits. |
| `blur.py in.jpg [out.jpg] [--boxes x,y,w,h;...]` | Blurs faces of private people (OpenCV YuNet; needs `pip install opencv-python-headless` + model in /home/claude/models/yunet.onnx from media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx). Writes `<name>_b.jpg`, copies the credit. Can hit doll/statue faces: only run it on photos with real people and check the result. |
| `sheet.py dir out.jpg` / `chk.sh video out.jpg` | Contact sheet of a photo folder / 14 frames of a finished video. |

Image paths in specs are relative to `/home/claude/partner/wk/`. `specs/jobs_week.txt` lists the Commons files chosen for this week; `specs/search_week.json` has more candidates per topic.

Big videos: commit to `videos/` here and give Metricool the raw URL
`https://raw.githubusercontent.com/angacebiz-dev/creepypartner-media/main/videos/<file>` (GitHub max ~100 MB per file).
