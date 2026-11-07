#!/usr/bin/env python3
"""Cut a long screen recording into a short edit: per-segment speed, seamless joins where footage is contiguous,
CROSSFADES where it jumps (hard cuts between different UI states flash, esp. dark→white), optional bottom crop.
usage: footage_edit.py rec.mp4 segments.json out.mp4 [--xfade 0.25] [--crop W:H:X:Y] [--start 2.6]
segments.json: [[footA, footB, speed], ...]  (seconds in the recording)
Writes out.mp4 and out_timing.json: [{"seg":i,"t0":projStart,"t1":projEnd,"speed":s}] (project time = --start + output time)
→ use the timing to place shots, spots, captions and ⏩ badges."""
import argparse, json, subprocess
a=argparse.ArgumentParser(); a.add_argument('rec'); a.add_argument('segs'); a.add_argument('out')
a.add_argument('--xfade',type=float,default=0.25); a.add_argument('--crop'); a.add_argument('--start',type=float,default=0)
o=a.parse_args(); S=json.load(open(o.segs))
# group contiguous segments (b_i == a_{i+1}) → concat inside a group, xfade between groups
groups=[[0]]
for i in range(1,len(S)):
    (groups[-1].append(i) if abs(S[i][0]-S[i-1][1])<1e-3 else groups.append([i]))
fc=[];gl=[];durs=[]
for gi,g in enumerate(groups):
    parts=[]
    for i in g:
        fa,fb,sp=S[i]; fc.append(f"[0:v]trim=start={fa}:end={fb},setpts=(PTS-STARTPTS)/{sp},fps=30,format=yuv420p[s{i}]"); parts.append(f"[s{i}]")
    fc.append(''.join(parts)+f"concat=n={len(parts)}:v=1:a=0,settb=1/30[g{gi}]" if len(parts)>1 else f"{parts[0]}settb=1/30[g{gi}]")
    durs.append(sum((S[i][1]-S[i][0])/S[i][2] for i in g))
X=o.xfade; cur='[g0]'; off=durs[0]; timing=[]
# timing: each group starts X earlier than the previous group's end (overlap)
gstart=[0.0]
for gi in range(1,len(groups)): gstart.append(gstart[-1]+durs[gi-1]-X)
for gi in range(1,len(groups)):
    nxt=f'[x{gi}]'; fc.append(f"{cur}[g{gi}]xfade=transition=fade:duration={X}:offset={gstart[gi]:.4f}{nxt}"); cur=nxt
tail=f",crop={o.crop}" if o.crop else ""
fc.append(f"{cur}null{tail}[out]")
subprocess.run(['ffmpeg','-v','error','-y','-i',o.rec,'-filter_complex',';'.join(fc),'-map','[out]','-c:v','libx264','-crf','14','-preset','fast','-pix_fmt','yuv420p',o.out],check=True)
for gi,g in enumerate(groups):
    t=gstart[gi]
    for i in g:
        d=(S[i][1]-S[i][0])/S[i][2]; timing.append({'seg':i,'t0':round(o.start+t,3),'t1':round(o.start+t+d,3),'speed':S[i][2]}); t+=d
json.dump(timing,open(o.out.rsplit('.',1)[0]+'_timing.json','w'),indent=1)
total=gstart[-1]+durs[-1]; print(f'{len(S)} segments in {len(groups)} groups, {len(groups)-1} crossfades → {total:.1f}s')
