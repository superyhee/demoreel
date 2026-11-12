#!/usr/bin/env python3
"""Render specific timestamps and tile them into one contact sheet for visual review.
usage: preview_sheet.py <page.html> <out.png> [--lang zh] [--aspect 9:16] t1 t2 ...   (any count; 3 columns)"""
import sys, os, argparse, math
from playwright.sync_api import sync_playwright
from PIL import Image
import sys as _s; _s.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_util import open_page, ASPECTS
a=argparse.ArgumentParser(); a.add_argument('page'); a.add_argument('out'); a.add_argument('--lang',default='zh'); a.add_argument('--cols',type=int,default=3); a.add_argument('--aspect',choices=ASPECTS); a.add_argument('ts',nargs='+',type=float)
o=a.parse_args()
tiles=[]
with sync_playwright() as p:
    b,pg,_,errs=open_page(p,o.page,o.lang,wait=600,aspect=o.aspect)
    if errs: sys.exit('page error: '+errs[0])
    for t in o.ts:
        pg.evaluate(f'render({t})'); fn=f'/tmp/_pv_{t}.png'; pg.screenshot(path=fn); im=Image.open(fn); tiles.append(im.resize((800,round(800*im.height/im.width))))
    b.close()
th=tiles[0].height; rows=math.ceil(len(tiles)/o.cols); sheet=Image.new('RGB',(800*o.cols,th*rows),'white')
for i,im in enumerate(tiles): sheet.paste(im,((i%o.cols)*800,(i//o.cols)*th))
sheet.save(o.out); print('sheet',o.out)
