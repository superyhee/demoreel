#!/usr/bin/env python3
"""Which seconds of a desktop recording show the INTENDED window? Compares the title-bar region of every frame (2 fps)
with a reference frame known to show the demo window. Use it to drop frames where other apps/windows came to front.
usage: footage_mask.py rec.mp4 --title-ref 40 --title-box 660,12,360,40 [--thr 12] [--json mask.json]
  --title-box x,y,w,h in recording pixels around the window's title text (e.g. the project name field)"""
import argparse, subprocess, tempfile, glob, json, os
import numpy as np
from PIL import Image
a=argparse.ArgumentParser(); a.add_argument('rec'); a.add_argument('--title-ref',type=float,required=True); a.add_argument('--title-box',required=True)
a.add_argument('--thr',type=float,default=12); a.add_argument('--json'); o=a.parse_args()
x,y,w,h=map(int,o.title_box.split(',')); d=tempfile.mkdtemp()
subprocess.run(['ffmpeg','-v','error','-i',o.rec,'-vf',f'fps=2,crop={w}:{h}:{x}:{y}',os.path.join(d,'p%05d.png')],check=True)
A=[np.asarray(Image.open(f).convert('L')).astype(float) for f in sorted(glob.glob(os.path.join(d,'p*.png')))]
ref=A[int(o.title_ref*2)]; ok=[float(np.abs(a_-ref).mean())<o.thr for a_ in A]
segs=[];cur=None
for i,k in enumerate(ok):
    if cur is None or cur[0]!=k: cur=[k,i/2,(i+1)/2]; segs.append(cur)
    else: cur[2]=(i+1)/2
for k,s0,s1 in segs: print(('OK   ' if k else 'OTHER'),f'{s0:7.1f}-{s1:7.1f}s')
print(f'usable {sum(ok)/2:.0f}s of {len(ok)/2:.0f}s')
if o.json: json.dump([[s0,s1] for k,s0,s1 in segs if k],open(o.json,'w'))
