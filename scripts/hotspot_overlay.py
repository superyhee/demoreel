#!/usr/bin/env python3
"""Draw hotspot boxes on prepped footage frames so you can SEE whether every camera/spotlight target matches the UI
(left/right/top/bottom margins). Do this before any render. Also prints the strongest vertical/horizontal UI edges near
each box side, so boxes can be snapped to real panel borders.
usage: hotspot_overlay.py <rec_dir> <hotspots.json | inline JSON> <out.png> [--frames 1,500,1700] [--snap 40]"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw
a=argparse.ArgumentParser(); a.add_argument('rec'); a.add_argument('hot'); a.add_argument('out'); a.add_argument('--frames',default='1')
a.add_argument('--snap',type=int,default=40); o=a.parse_args()
H=json.load(open(o.hot)) if os.path.exists(o.hot) else json.loads(o.hot)
tiles=[]
for n in [int(x) for x in o.frames.split(',')]:
    im=Image.open(os.path.join(o.rec,f'f{n:05d}.jpg')).convert('RGB'); g=np.asarray(im.convert('L')).astype(float); d=ImageDraw.Draw(im)
    for k,(x,y,w,h) in H.items():
        d.rectangle([x,y,x+w,y+h],outline=(255,60,60),width=4); d.text((x+6,y+4),k,fill=(255,230,0))
        if n==int(o.frames.split(',')[0]):
            def edge(axis,pos,lo,hi):   # strongest edge within ±snap of pos
                r=range(max(1,pos-o.snap),min((g.shape[1] if axis=='x' else g.shape[0])-1,pos+o.snap))
                prof=[np.abs(g[lo:hi,p]-g[lo:hi,p-1]).mean() if axis=='x' else np.abs(g[p,lo:hi]-g[p-1,lo:hi]).mean() for p in r]
                return list(r)[int(np.argmax(prof))] if len(prof) else pos   # box touches the frame edge
            print(f"{k:14s} box x {x}-{x+w} y {y}-{y+h} | nearest UI edges: L {edge('x',x,y,y+h)} R {edge('x',x+w,y,y+h)} T {edge('y',y,x,x+w)} B {edge('y',y+h,x,x+w)}")
    tiles.append(im.resize((im.width//2,im.height//2)))
W=sum(t.width for t in tiles); S=Image.new('RGB',(W,tiles[0].height)); x=0
for t in tiles: S.paste(t,(x,0)); x+=t.width
S.save(o.out); print('overlay ->',o.out)
