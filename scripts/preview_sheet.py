#!/usr/bin/env python3
"""Render specific timestamps and tile them into one contact sheet for visual review.
usage: preview_sheet.py <page.html> <out.png> [--lang zh] t1 t2 ...   (any count; 3 columns)"""
import sys, os, argparse, math
from playwright.sync_api import sync_playwright
from PIL import Image
a=argparse.ArgumentParser(); a.add_argument('page'); a.add_argument('out'); a.add_argument('--lang',default='zh'); a.add_argument('--cols',type=int,default=3); a.add_argument('ts',nargs='+',type=float)
o=a.parse_args(); url='file://'+os.path.abspath(o.page)+f'?lang={o.lang}'
tiles=[]
with sync_playwright() as p:
    b=p.chromium.launch(channel='chrome'); pg=b.new_page(viewport={'width':1920,'height':1080})
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.goto(url); pg.wait_for_timeout(600)
    if errs: sys.exit('page error: '+errs[0])
    for t in o.ts:
        pg.evaluate(f'render({t})'); fn=f'/tmp/_pv_{t}.png'; pg.screenshot(path=fn); tiles.append(Image.open(fn).resize((800,450)))
    b.close()
rows=math.ceil(len(tiles)/o.cols); sheet=Image.new('RGB',(800*o.cols,450*rows),'white')
for i,im in enumerate(tiles): sheet.paste(im,((i%o.cols)*800,(i//o.cols)*450))
sheet.save(o.out); print('sheet',o.out)
