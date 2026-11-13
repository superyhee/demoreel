#!/usr/bin/env python3
"""Framing QA for every camera shot BEFORE rendering: samples the middle of each hold and reports
  app coverage of the screen · left/right & top/bottom margins (symmetry) · whether the target is covered by the caption.
Wide shots = holds whose target is the bounds selector itself (e.g. '#win'), sampled after camIn.
Rules (best practice): WIDE shots → app spans 85–95 % of the screen's limiting dimension (equal margins), |L−R| ≤ 20 px; CLOSE-UPs → app ≥ 98 % (no empty canvas),
target fully below the caption band and inside the screen.
usage: shot_qa.py <page.html> [--lang zh] [--aspect 9:16] [--bounds '#win']
frameRule 'fit' (portrait/square default): close-ups are judged by how much of the view the TARGET fills, not the app."""
import argparse, os, json
from playwright.sync_api import sync_playwright
import sys as _s; _s.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_util import open_page, ASPECTS
a=argparse.ArgumentParser(); a.add_argument('page'); a.add_argument('--lang',default='zh'); a.add_argument('--bounds',default=None); a.add_argument('--aspect',choices=ASPECTS); o=a.parse_args()
with sync_playwright() as p:
    b,pg,_,_=open_page(p,o.page,o.lang,aspect=o.aspect)
    fit=pg.evaluate("(window.DEMO_CFG||{}).frameRule==='fit'")
    res=pg.evaluate("""async(bsel)=>{const C=window.DEMO_CFG,K=C.cam,B=bsel||C.camBounds||'#win',out=[],W=innerWidth,H=innerHeight;
      for(let i=0;i<K.length-1;i++){if(JSON.stringify(K[i][1])!==JSON.stringify(K[i+1][1]))continue;   // holds only
        const ci=C.camIn?C.camIn[1]+0.15:0,co=C.camOut?C.camOut[0]-0.05:1e9;const t=Math.min(co,Math.max((K[i][0]+K[i+1][0])/2,ci));   // sample after entry / before exit
        await render(t);
        const r=document.querySelector(B).getBoundingClientRect();
        const ix=Math.max(0,Math.min(W,r.right)-Math.max(0,r.left)),iy=Math.max(0,Math.min(H,r.bottom)-Math.max(0,r.top));
        let tx=[1e9,1e9,-1e9,-1e9];for(const s of K[i][1]){const e=document.querySelector(s);if(!e)continue;const q=e.getBoundingClientRect();tx=[Math.min(tx[0],q.left),Math.min(tx[1],q.top),Math.max(tx[2],q.right),Math.max(tx[3],q.bottom)];}
        const cap=document.querySelector('#cap'),cr=cap&&getComputedStyle(cap).opacity>0.05?cap.getBoundingClientRect():null;
        const capHit=cr?Math.max(0,Math.min(cr.bottom,tx[3])-Math.max(cr.top,tx[1]))*Math.max(0,Math.min(cr.right,tx[2])-Math.max(cr.left,tx[0])):0;
        out.push({lin:Math.max(ix/W,iy/H),t:+t.toFixed(2),sel:K[i][1].join(','),wide:K[i][1].includes(B),cov:ix*iy/(W*H),tw:(tx[2]-tx[0])/C.view.w,th:(tx[3]-tx[1])/C.view.h,L:Math.round(r.left),R:Math.round(W-r.right),T:Math.round(r.top),Bm:Math.round(H-r.bottom),
          capHit:Math.round(capHit),offL:tx[0]<-2,offR:tx[2]>W+2,offY:tx[3]>H+2});}
      return out}""",o.bounds)
    b.close()
bad=0
print(f"{'t':>7} {'type':5} {'cover':>6} {'L':>5} {'R':>5} {'T':>5} {'B':>5}  target / issues")
for r in res:
    iss=[]
    if r['wide']:
        if not .85<=r['lin']<=.95: iss.append(f"wide framing {r['lin']*100:.0f}% of the limiting dimension (want 85–95)")
        if abs(r['L']-r['R'])>20: iss.append(f"L/R margins unequal ({r['L']} vs {r['R']})")
    else:
        if fit:
            if max(r['tw'], r['th']) < .8: iss.append(f"close-up target fills only {max(r['tw'], r['th'])*100:.0f}% of the view (want ≥ 80)")
        elif r['cov']<.98: iss.append(f"close-up shows empty canvas ({r['cov']*100:.0f}%)")
        if r['capHit']>0: iss.append(f"caption covers target ({r['capHit']} px²)")
        # 'fit': a target wider than the view is cropped on the RIGHT on purpose (its start stays in frame)
        if r['offL'] or r['offY'] or (r['offR'] and not fit): iss.append("target partly off-screen")
    bad+=bool(iss)
    print(f"{r['t']:7.2f} {'WIDE' if r['wide'] else 'CLOSE':5} {r['cov']*100:5.0f}% {r['L']:5} {r['R']:5} {r['T']:5} {r['Bm']:5}  {r['sel'][:38]:38} {'; '.join(iss) or 'ok'}")
print(f"\n{len(res)} holds checked, {bad} with issues")
