#!/usr/bin/env python3
"""Record a REAL web app session deterministically with Playwright (no desktop, no private windows captured).
usage: record_web.py <url> <out.mp4> --steps steps.json [--size 1440x900] [--slowmo 0] [--log events.json]
steps.json: list of actions, executed in order; every step can carry "pause": seconds to wait afterwards.
  {"goto": "https://..."}  {"click": "css"}  {"type": ["css", "text", 60]}   # 60 ms per key (human-like)
  {"press": "Enter"}  {"hover": "css"}  {"scroll": 600}  {"wait": 1.5}  {"waitFor": "css"}  {"mark": "name"}
Writes <out.mp4> (constant 30 fps) and an events log with the recording time of every step/mark, so the
storyboard / time-map can be planned against real timings. Use a DEMO account — never record real customer data."""
import argparse, json, time, os, subprocess, tempfile, shutil, base64
from playwright.sync_api import sync_playwright
a=argparse.ArgumentParser(); a.add_argument('url'); a.add_argument('out'); a.add_argument('--steps',required=True)
a.add_argument('--size',default='1440x900'); a.add_argument('--slowmo',type=int,default=0); a.add_argument('--log')
o=a.parse_args(); W,Hh=map(int,o.size.split('x')); steps=json.load(open(o.steps)); tmp=tempfile.mkdtemp()
url=o.url if '://' in o.url else 'file://'+os.path.abspath(o.url)
ev=[]
with sync_playwright() as p:
    b=p.chromium.launch(channel='chrome',slow_mo=o.slowmo,args=[f'--window-size={W},{Hh}'])
    ctx=b.new_context(viewport={'width':W,'height':Hh},screen={'width':W,'height':Hh})
    pg=ctx.new_page(); pg.goto(url); pg.wait_for_load_state('networkidle')
    # Chrome's own screencast stream (no extra Playwright ffmpeg download): timestamped JPEG frames
    cdp=ctx.new_cdp_session(pg); frames=[]
    def on_frame(e):
        frames.append((e['metadata']['timestamp'], base64.b64decode(e['data']))); cdp.send('Page.screencastFrameAck',{'sessionId':e['sessionId']})
    cdp.on('Page.screencastFrame',on_frame)
    cdp.send('Page.startScreencast',{'format':'jpeg','quality':92,'maxWidth':W,'maxHeight':Hh,'everyNthFrame':1})
    pg.wait_for_timeout(300); t0=time.time(); wall0=None
    for st in steps:
        ev.append({'t':round(time.time()-t0,3),'step':st})
        if 'goto' in st: pg.goto(st['goto']); pg.wait_for_load_state('networkidle')
        if 'click' in st: pg.click(st['click'])
        if 'hover' in st: pg.hover(st['hover'])
        if 'type' in st: sel,txt,*d=st['type']; pg.click(sel); pg.keyboard.type(txt,delay=(d[0] if d else 60))
        if 'press' in st: pg.keyboard.press(st['press'])
        if 'scroll' in st: pg.mouse.wheel(0,st['scroll'])
        if 'waitFor' in st: pg.wait_for_selector(st['waitFor'])
        if 'wait' in st: pg.wait_for_timeout(int(st['wait']*1000))
        if 'pause' in st: pg.wait_for_timeout(int(st['pause']*1000))
    pg.wait_for_timeout(600); cdp.send('Page.stopScreencast'); ctx.close(); b.close()
# screencast only emits frames when the page changes → hold each frame until the next one, then resample to 30 fps
ts0=frames[0][0]; lst=os.path.join(tmp,'list.txt')
with open(lst,'w') as L:
    for i,(ts,data) in enumerate(frames):
        fn=os.path.join(tmp,f'{i:06d}.jpg'); open(fn,'wb').write(data)
        dur=(frames[i+1][0]-ts) if i+1<len(frames) else 0.5
        L.write(f"file '{fn}'\nduration {max(dur,0.001):.4f}\n")
    L.write(f"file '{fn}'\n")
subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',lst,'-vf',f'fps=30,scale={W}:{Hh}:flags=lanczos,format=yuv420p','-c:v','libx264','-crf','14','-preset','medium',o.out],check=True)
for e in ev: e['t']=round(e['t']-(ts0-ts0),3)
json.dump(ev,open(o.log or os.path.splitext(o.out)[0]+'_events.json','w'),ensure_ascii=False,indent=1); shutil.rmtree(tmp,ignore_errors=True)
print('recorded',o.out,f'{W}x{Hh}',f'{len(steps)} steps')
