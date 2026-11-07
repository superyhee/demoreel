#!/usr/bin/env python3
"""Turn a screen recording into an image sequence the engine's `footage` layer can play frame-accurately.
usage: footage_prep.py <rec.mp4> <out_dir> [--fps 30] [--crop x:y:w:h] [--width 1600] [--q 2]
Writes out_dir/f00001.jpg … and prints the JS config snippet (w, h, frames, fps) to paste into Demo.init footage:[…]."""
import argparse, subprocess, os, json, glob
from PIL import Image
a=argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('out'); a.add_argument('--fps',type=int,default=30)
a.add_argument('--crop'); a.add_argument('--width',type=int); a.add_argument('--q',type=int,default=2); a.add_argument('--deflash',type=float,default=8.0,help='luminance threshold for single-frame flash removal (0=off)'); a.add_argument('--smooth-steps',type=float,default=20.0,help='luminance step that gets a short dissolve (0=off)'); a.add_argument('--smooth-frames',type=int,default=6)
o=a.parse_args(); os.makedirs(o.out,exist_ok=True)
vf=[f'fps={o.fps}']
if o.crop: x,y,w,h=o.crop.split(':'); vf.append(f'crop={w}:{h}:{x}:{y}')
if o.width: vf.append(f'scale={o.width}:-2:flags=lanczos')
subprocess.run(['ffmpeg','-v','error','-y','-i',o.src,'-vf',','.join(vf),'-q:v',str(o.q),os.path.join(o.out,'f%05d.jpg')],check=True)
fr=sorted(glob.glob(os.path.join(o.out,'f*.jpg')))
# de-flash: apps sometimes repaint one bright/dark frame; at 10× speed that reads as a flash → replace single-frame
# luminance outliers (|Δ| to BOTH neighbours > thr, neighbours agree) with the previous frame
from PIL import ImageStat
import shutil
Lm=[ImageStat.Stat(Image.open(f).convert('L').resize((160,100))).mean[0] for f in fr] if True else []
fixed=0
for i in range(1,len(fr)-1 if o.deflash>0 else 1):
    if abs(Lm[i]-Lm[i-1])>o.deflash and abs(Lm[i]-Lm[i+1])>o.deflash and abs(Lm[i-1]-Lm[i+1])<o.deflash/2:
        shutil.copy(fr[i-1],fr[i]); Lm[i]=Lm[i-1]; fixed+=1
if fixed: print(f'de-flashed {fixed} single-frame outliers')
# smooth hard UI steps (e.g. a dark editor turning into a white document in one frame): dissolve over N frames
if o.smooth_steps>0:
    N=o.smooth_frames; steps=0; i=1
    while i<len(fr)-N:
        if abs(Lm[i]-Lm[i-1])>o.smooth_steps and abs(Lm[min(i+N,len(Lm)-1)]-Lm[i])<o.smooth_steps/2:   # a STEP (stays changed)
            A=Image.open(fr[i-1]).convert('RGB'); B=[Image.open(fr[i+k]).convert('RGB') for k in range(N)]
            for k in range(N): Image.blend(A,B[k],(k+1)/(N+1)).save(fr[i+k],quality=95)
            steps+=1; i+=N
        i+=1
    if steps: print(f'smoothed {steps} hard brightness steps over {N} frames')

w,h=Image.open(fr[0]).size
meta={'w':w,'h':h,'frames':len(fr),'fps':o.fps,'duration':round(len(fr)/o.fps,3)}; json.dump(meta,open(os.path.join(o.out,'meta.json'),'w'))
rel=os.path.relpath(o.out)+'/f'
print(json.dumps(meta)); print(f"footage:[{{el:'#rec', src:'{rel}', ext:'jpg', fps:{o.fps}, frames:{len(fr)}, w:{w}, h:{h}, map:[[START,0],[START+{meta['duration']},{meta['duration']}]], hotspots:{{}}}}]")
