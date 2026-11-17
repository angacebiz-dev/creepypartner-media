"""Blur faces of private people in a photo (keeps the real photo, protects identities).
  python3 blur.py <in.jpg> [out.jpg] [--boxes x,y,w,h;x,y,w,h] [--thresh 0.6] [--show sheet.jpg]
Auto-detects faces with OpenCV YuNet (multi-scale + tiled so small faces are found), adds any manual boxes,
then applies a heavy blur + slight darkening to each face (padded). Writes <name>_b.jpg by default and copies
the credit entry in credits.json. Prints the boxes it blurred so they can be checked on a sheet.
Model: /home/claude/models/yunet.onnx (opencv_zoo face_detection_yunet_2023mar.onnx).
"""
import json, os, sys
import cv2
import numpy as np

MODEL = "/home/claude/models/yunet.onnx"


def detect(img, thresh=0.6):
    H, W = img.shape[:2]
    boxes = []
    for scale in (1.0, 2.0, 3.0):  # upscale to catch small faces (crowds, newspaper photos)
        im = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale != 1 else img
        h, w = im.shape[:2]
        tile = 640
        for y0 in range(0, max(1, h - tile // 2), tile // 2):
            for x0 in range(0, max(1, w - tile // 2), tile // 2):
                crop = im[y0:y0 + tile, x0:x0 + tile]
                ch, cw = crop.shape[:2]
                if ch < 40 or cw < 40:
                    continue
                det = cv2.FaceDetectorYN.create(MODEL, "", (cw, ch), thresh, 0.3, 5000)
                _, faces = det.detect(crop)
                if faces is None:
                    continue
                for f in faces:
                    x, y, fw, fh = f[:4]
                    boxes.append([(x + x0) / scale, (y + y0) / scale, fw / scale, fh / scale])
    # merge overlapping boxes
    out = []
    for b in sorted(boxes, key=lambda b: -b[2] * b[3]):
        cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
        if any(o[0] <= cx <= o[0] + o[2] and o[1] <= cy <= o[1] + o[3] for o in out):
            continue
        out.append(b)
    return [[int(v) for v in b] for b in out]


def blur_boxes(img, boxes, pad=0.35):
    H, W = img.shape[:2]
    for x, y, w, h in boxes:
        px, py = int(w * pad), int(h * pad)
        x0, y0, x1, y1 = max(0, x - px), max(0, y - py), min(W, x + w + px), min(H, y + h + py)
        roi = img[y0:y1, x0:x1]
        if roi.size == 0:
            continue
        k = max(15, (max(roi.shape[:2]) // 2) | 1)
        small = cv2.resize(roi, (max(1, roi.shape[1] // 10), max(1, roi.shape[0] // 10)), interpolation=cv2.INTER_LINEAR)
        b = cv2.resize(small, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_LINEAR)
        b = cv2.GaussianBlur(b, (k, k), 0)
        b = (b.astype(np.float32) * 0.85).astype(np.uint8)
        # soft elliptical mask so the blur blends in
        m = np.zeros(roi.shape[:2], np.float32)
        cv2.ellipse(m, (roi.shape[1] // 2, roi.shape[0] // 2), (roi.shape[1] // 2, roi.shape[0] // 2), 0, 0, 360, 1, -1)
        m = cv2.GaussianBlur(m, (31, 31), 0)[..., None]
        img[y0:y1, x0:x1] = (b * m + roi * (1 - m)).astype(np.uint8)
    return img


if __name__ == "__main__":
    a = sys.argv[1:]
    src = a[0]
    dst = a[1] if len(a) > 1 and not a[1].startswith("--") else os.path.splitext(src)[0] + "_b.jpg"
    thresh = float(a[a.index("--thresh") + 1]) if "--thresh" in a else 0.6
    img = cv2.imread(src)
    boxes = detect(img, thresh)
    if "--boxes" in a:
        for s in a[a.index("--boxes") + 1].split(";"):
            boxes.append([int(v) for v in s.split(",")])
    img = blur_boxes(img, boxes)
    cv2.imwrite(dst, img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    cf = os.path.join(os.path.dirname(os.path.abspath(src)), "credits.json")
    if os.path.exists(cf):
        c = json.load(open(cf)); k = os.path.basename(src)
        if k in c:
            c[os.path.basename(dst)] = c[k]; json.dump(c, open(cf, "w"), indent=1)
    print(dst, "blurred", len(boxes), "faces:", boxes)
