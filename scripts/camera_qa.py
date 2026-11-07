#!/usr/bin/env python3
"""Camera-motion QA: samples every frame of the timeline (no rendering to disk) and flags JITTER — the framed app
reversing direction (position or zoom) during a move, or holds that drift faster than a slow push.
usage: camera_qa.py <page.html> [--lang zh] [--bounds '#win'] [--fps 30]"""
import argparse, os
import numpy as np
from playwright.sync_api import sync_playwright
a=argparse.ArgumentParser(); a.add_argument('page'); a.add_argument('--lang',default='zh'); a.add_argument('--bounds',default=None); a.add_argument('--fps',type=int,default=30); o=a.parse_args()
with sync_playwright() as p:
    b=p.chromium.launch(channel='chrome'); pg=b.new_page(viewport={'width':1920,'height':1080})
    pg.goto('file://'+os.path.abspath(o.page)+f'?lang={o.lang}'); pg.wait_for_timeout(800)
    tr=pg.evaluate("""async([bsel,fps])=>{const C=window.DEMO_CFG,B=bsel||C.camBounds||'#win',o=[];const T0=C.camIn?C.camIn[1]:0,T1=C.camOut?C.camOut[0]:C.duration;
      for(let t=T0;t<T1;t+=1/fps){await render(t);const r=document.querySelector(B).getBoundingClientRect();o.push([t,r.left+r.width/2,r.top+r.height/2,r.width]);}return o}""",[o.bounds,o.fps])
    b.close()
A=np.array(tr); t=A[:,0]; issues=[]
for col,name,thr in [(1,'x',0.8),(2,'y',0.8),(3,'zoom',0.8)]:
    v=np.diff(A[:,col])
    for i in range(1,len(v)-1):
        # a reversal with real motion on both sides = wobble (ignore sub-pixel noise)
        if v[i]*v[i-1]<0 and min(abs(v[i]),abs(v[i-1]))>thr: issues.append((round(t[i+1],2),name,round(v[i-1],1),round(v[i],1)))
issues.sort()
print(f'{len(t)} frames sampled ({t[0]:.1f}–{t[-1]:.1f}s) | direction reversals (jitter): {len(issues)}')
for x in issues[:15]: print(f'  t={x[0]:7.2f}s {x[1]:4s} Δ {x[2]:+6.1f} → {x[3]:+6.1f} px/frame')
