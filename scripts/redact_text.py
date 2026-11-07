#!/usr/bin/env python3
"""Blur a private word (user name, email, account id…) everywhere it appears in footage frames, by template matching
crops of the word as rendered by the app (one crop per font/size/background it appears in).

usage: redact_text.py rec/ --tpl f01960.jpg:1449,757,95,26 --tpl f01960.jpg:1467,817,88,24 [--thr 0.72] [--pad 3]
                      [--backup rec_noredact/] [--report hits.json] [--workers 8]
  --tpl FRAME:x,y,w,h   a crop of the word in a frame of rec/ (footage px). Add one per font size / background.
Each frame: all matches ≥ thr (NMS) get a strong Gaussian blur (+ slight darken) over the word box + pad.
Idempotent when run on a pristine copy: reads from --backup, writes into rec/.
Verify afterwards: grep the report for frame ranges and Read a few frames — template matching misses partial/scrolling words.
"""
import argparse, glob, json, os, shutil
import numpy as np, cv2
from concurrent.futures import ProcessPoolExecutor

def hits_in(g, T, thr):
    out = []
    for t in T:
        r = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED); h, w = t.shape
        ys, xs = np.where(r >= thr)
        for y, x in sorted(zip(ys, xs), key=lambda p: -r[p[0], p[1]]):
            if all(abs(x - a) > w // 2 or abs(y - b) > h // 2 for a, b, _, _ in out): out.append((int(x), int(y), w, h))
    return out

def work(a):
    paths, src, T, thr, pad = a; T = [cv2.imread(p, 0) for p in T]; rep = {}
    for p in paths:
        img = cv2.imread(os.path.join(src, os.path.basename(p))); g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hs = hits_in(g, T, thr)
        for x, y, w, h in hs:
            x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(img.shape[1], x + w + pad), min(img.shape[0], y + h + pad)
            roi = img[y0:y1, x0:x1]; img[y0:y1, x0:x1] = (cv2.GaussianBlur(roi, (0, 0), 7) * 0.92).astype(np.uint8)
        if hs: rep[os.path.basename(p)] = hs
        cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return rep

def main():
    a = argparse.ArgumentParser(); a.add_argument('rec'); a.add_argument('--tpl', action='append', required=True)
    a.add_argument('--thr', type=float, default=0.72); a.add_argument('--pad', type=int, default=3)
    a.add_argument('--backup', required=True); a.add_argument('--report'); a.add_argument('--workers', type=int, default=8)
    o = a.parse_args()
    if not os.path.exists(o.backup): shutil.copytree(o.rec, o.backup)
    tp = []
    for i, s in enumerate(o.tpl):
        fr, box = s.split(':'); x, y, w, h = map(int, box.split(','))
        g = cv2.imread(os.path.join(o.backup, fr), 0)[y:y + h, x:x + w]; p = os.path.join(o.backup, f'_tpl{i}.png'); cv2.imwrite(p, g); tp.append(p)
    P = sorted(glob.glob(os.path.join(o.rec, 'f*.jpg'))); n = o.workers
    with ProcessPoolExecutor(n) as ex: reps = list(ex.map(work, [(P[i::n], o.backup, tp, o.thr, o.pad) for i in range(n)]))
    rep = {k: v for r in reps for k, v in r.items()}
    if o.report: json.dump(rep, open(o.report, 'w'))
    print(f'redacted {sum(len(v) for v in rep.values())} occurrences in {len(rep)}/{len(P)} frames')

if __name__ == '__main__':
    main()
