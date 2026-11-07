#!/usr/bin/env python3
"""Crop the REAL logo out of a screenshot and key out its flat background (never redraw a logo).
usage: logo_alpha.py <screenshot.png> <x> <y> <w> <h> <out.png> [softness=60]   (pixel coords of the full-res screenshot)"""
import sys
from PIL import Image
src,x,y,w,h,out=sys.argv[1],*map(int,sys.argv[2:6]),sys.argv[6]; soft=int(sys.argv[7]) if len(sys.argv)>7 else 60
im=Image.open(src).convert('RGBA').crop((x,y,x+w,y+h)); px=im.load(); bg=px[1,1][:3]
for j in range(h):
    for i in range(w):
        r,g,b,_=px[i,j]; d=max(abs(r-bg[0]),abs(g-bg[1]),abs(b-bg[2])); px[i,j]=(r,g,b,min(255,int(d*255/soft)))
im.save(out); print(out,'bg=',bg)
