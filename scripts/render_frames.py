#!/usr/bin/env python3
"""Render a DEMO page frame-by-frame with system Chrome (deterministic, uses window.render(t)).
usage: render_frames.py <page.html> <out_dir> [--lang zh] [--from F] [--to F] [--dsf 1]
Also writes <out_dir>/../sfx_<lang>.json from window.SFX (feed it to sfx.py)."""
import sys, os, json, argparse
from playwright.sync_api import sync_playwright
a=argparse.ArgumentParser(); a.add_argument('page'); a.add_argument('out'); a.add_argument('--lang',default='zh')
a.add_argument('--from',dest='f0',type=int,default=0); a.add_argument('--to',dest='f1',type=int,default=None); a.add_argument('--dsf',type=float,default=1)
o=a.parse_args(); os.makedirs(o.out,exist_ok=True)
url='file://'+os.path.abspath(o.page)+f'?lang={o.lang}'
with sync_playwright() as p:
    b=p.chromium.launch(channel='chrome')   # bundled chromium is often missing; system Chrome works
    pg=b.new_page(viewport={'width':1920,'height':1080},device_scale_factor=o.dsf)
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(800)
    if errs: sys.exit('page error: '+errs[0])
    fps=pg.evaluate('window.FPS||30'); dur=pg.evaluate('window.DURATION||30')
    json.dump(pg.evaluate('window.SFX||[]'),open(os.path.join(os.path.dirname(os.path.abspath(o.out)),f'sfx_{o.lang}.json'),'w'))
    f1=o.f1 if o.f1 is not None else int(round(fps*dur))
    for f in range(o.f0,f1):
        pg.evaluate(f'render({f/fps})'); pg.screenshot(path=f'{o.out}/f{f:04d}.png')
        if f%150==0: print('frame',f,flush=True)
    b.close()
print('done',o.out)
