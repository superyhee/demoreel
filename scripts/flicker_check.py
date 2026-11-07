#!/usr/bin/env python3
"""Detect visual flicker in rendered frames: a global-brightness spike that reverses within a few frames
(e.g. a spotlight fading out then in). Smooth fades (same-direction changes) are not flagged.
usage: flicker_check.py <frames_dir> [--fps 30] [--from F] [--to F] [--thr 1.2]"""
import argparse, glob, os
from PIL import Image, ImageStat
a=argparse.ArgumentParser(); a.add_argument('dir'); a.add_argument('--fps',type=float,default=30); a.add_argument('--from',dest='f0',type=int,default=0); a.add_argument('--to',dest='f1',type=int); a.add_argument('--thr',type=float,default=3.0)   # ≥3/255 luminance per frame is the visible threshold
o=a.parse_args(); files=sorted(glob.glob(os.path.join(o.dir,'f*.png')))[o.f0:o.f1]
L=[ImageStat.Stat(Image.open(f).convert('L').resize((240,135))).mean[0] for f in files]; d=[L[i+1]-L[i] for i in range(len(L)-1)]
sp=[round((i+o.f0)/o.fps,2) for i in range(len(d)-4) if abs(d[i])>o.thr and any(d[j]*d[i]<0 and abs(d[j])>o.thr for j in range(i+1,i+5))]
print(f'frames {len(L)} | flicker spikes: {len(sp)} {sp[:20]} | max single-frame Δ {max(map(abs,d)):.2f}')
