#!/usr/bin/env python3
"""Commercial-quality gate for ANY demo page (simulated UI or real footage). Run before rendering; fix every FAIL.

usage: commercial_qa.py site/index.html [--lang zh] [--aspect 9:16] [--frames 24]
Checks (automatic):
  hook          something readable on screen before 3 s (not a blank/logo-only opening)
  length        ≤ 100 s for one storyline (longer → offer a 60–90 s cut), ≥ 10 s
  subtitles     VO-synced subtitles configured (subtitle_marks.py → subs.js) and covering ≥ 35 % of the runtime
  headlines     headline captions ≤ 3.5 s each (except 'hold'), on screen ≤ 55 % of the runtime (restraint)
  spotlight     dim ≤ 0.4, blur ≤ 1.6 (murky films read as amateur)
  framing       camBounds set, no minimap; shot_qa.py 0 issues; camera_qa.py 0 direction reversals
  clutter       ≤ 3 overlay layers at once (headline, subtitles, callouts, clock, cards, badges)
  text size     ≥ 70 % of visible UI text ≥ 14 px on screen during camera holds (phone viewers)
  brightness    mean luma of content frames ≥ 30 (dark UIs look darker on video)
  end card      exactly ONE call-to-action visible in the last 3 s; cursor hidden on the end card
  focus aids    at least one callout (notes) or spotlight in a ≥ 20 s film
  hold still    the camera does not drift during holds and no text creeps sub-pixel for ≥ 0.4 s (text shimmer)
  logo          no placeholder logo from templates/ (copy the REAL one: scripts/app_logo.py / logo_alpha.py)
  establish     the first camera shot after camIn is a WIDE hold ≥ 1.2 s (orient the viewer before the first push-in)
  beat sync     camera-move arrivals + headline starts land within 60 ms of a beat (beats.js from beat_grid.py), ≥ 60 %
  callouts in frame   every visible callout box stays inside the frame
  headline clear      the headline pill never covers the camera's hold target (FAIL); subtitles clear: same for subtitles (WARN)
  headline wrap       no headline wraps into a lone short last line (WARN)
  brand name    the product name on the end card also appears in the VO script (../vo_<lang>.tsv) — catches renamed brands
Manual (always listed): licensed music, human/natural VO, facts & brand review, 3–5 viewers on a phone.
Exit code 1 if any FAIL.
"""
import argparse, os, re, subprocess, sys, io, hashlib
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_util import open_page, cam_segments, ASPECTS

S = os.path.dirname(os.path.abspath(__file__))
OVER = ['#cap', '#subs', '#speed', '[id^="dnB"]', '.card', '#mm', '#persona']
CTA_RE = r'(下载|免费|试用|立即|开始使用|打开|预约|联系|\bGet started\b|\bTry\b|\bDownload\b|\bSign up\b|\bBook\b|\bStart free\b|\bLearn more\b|\bOpen\b)'

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True); return r.stdout + r.stderr

# Per-frame layout geometry, sampled every 0.1 s in ONE round trip. "target" = the camera's hold target (not wide shots).
LAYOUT_JS = '''(ts)=>{const C=DEMO_CFG,K=C.cam,B=C.camBounds,W=innerWidth,Hh=innerHeight;
  const vis=e=>{if(!e)return 0;let x=e,op=1;while(x&&x!==document.body){const s=getComputedStyle(x);if(s.display==='none')return 0;op*=+s.opacity;x=x.parentElement;}return op;};
  const R=e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom];};
  const inter=(a,b)=>[Math.max(0,Math.min(a[2],b[2])-Math.max(a[0],b[0])),Math.max(0,Math.min(a[3],b[3])-Math.max(a[1],b[1]))];
  const target=t=>{for(let i=0;i<K.length-1;i++)if(t>=K[i][0]&&t<K[i+1][0]){if(JSON.stringify(K[i][1])!==JSON.stringify(K[i+1][1])||(B&&K[i][1].includes(B)))return null;
      let u=null;for(const s of K[i][1]){const e=document.querySelector(s);if(!e)continue;const r=R(e);if(r[2]-r[0]<2)continue;u=u?[Math.min(u[0],r[0]),Math.min(u[1],r[1]),Math.max(u[2],r[2]),Math.max(u[3],r[3])]:r;}return u;}return null;};
  const lines=e=>{const rg=document.createRange();rg.selectNodeContents(e);const by={};for(const r of rg.getClientRects()){if(r.width<1)continue;const k=Math.round(r.top/8);
      by[k]=by[k]?[Math.min(by[k][0],r.left),Math.max(by[k][1],r.right)]:[r.left,r.right];}return Object.keys(by).sort((a,b)=>a-b).map(k=>by[k][1]-by[k][0]);};
  return ts.map(t=>{render(t);const o={t,off:[],cap:0,subs:0,orphan:null};const tg=target(t);
    document.querySelectorAll('[id^="dnB"]').forEach(e=>{if(vis(e)<0.5)return;const r=R(e),d=Math.max(-r[0],-r[1],r[2]-W,r[3]-Hh);if(d>6)o.off.push(Math.round(d));});
    const cap=document.querySelector('#cap');if(cap&&vis(cap)>0.5&&cap.textContent.trim()){if(tg){const i=inter(R(cap),tg);if(i[0]>8&&i[1]>8)o.cap=Math.round(i[1]);}
      const L=lines(cap);if(L.length>1&&L[L.length-1]<0.3*Math.max(...L))o.orphan=cap.textContent.trim();}
    const sb=document.querySelector('#subs');if(sb&&tg&&vis(sb)>0.5&&sb.textContent.trim()){const i=inter(R(sb),tg);if(i[0]>8&&i[1]>12)o.subs=Math.round(i[1]);}
    return o;})}'''

def spans(ts):
    """[0.1 s samples] → 'a–b s, c–d s' (merged runs)"""
    out = []
    for t in ts:
        if out and t - out[-1][1] <= 0.15: out[-1][1] = t
        else: out.append([t, t])
    return ', '.join(f'{a:g}–{b:g}s' if b > a else f'{a:g}s' for a, b in out[:4]) + (' …' if len(out) > 4 else '')

def layout_checks(pg, D, add):
    """Collisions the eye catches at once but the other checks miss (all found by visual_review on a real film):
    callouts off-frame, headline / subtitles over the camera's hold target, a headline wrapped into a lone last word.
    (An 'empty canvas' metric — flat-tile share / largest empty band — was tried and dropped: it scored a reviewer-flagged
    layout and its fix the same. Empty frames stay a visual_review item.)"""
    ts = [round(k / 10, 1) for k in range(int(D * 10))]
    r = pg.evaluate(LAYOUT_JS, ts)
    off = [x['t'] for x in r if x['off']]; cap = [x['t'] for x in r if x['cap']]; sub = [x['t'] for x in r if x['subs']]
    orph = sorted({x['orphan'] for x in r if x['orphan']})
    add('callouts in frame', not off, 'every visible callout box is inside the frame' if not off else
        f'callout box leaves the frame at {spans(off)} (by {max(max(x["off"]) for x in r if x["off"])} px) → shrink the box / sel to what the camera shows')
    add('headline clear', not cap, 'headline never covers the hold target' if not cap else
        f'headline pill covers the hold target at {spans(cap)} → raise captionSafe, move the target down, or shorten the hold under the headline')
    add('subtitles clear', not sub, 'subtitles never cover the hold target' if not sub else
        f'subtitles cover the hold target at {spans(sub)} → bottomSafe ≥ subtitle height, a smaller target, or subtitles:{{position:"auto"}}', warn=True)
    add('headline wrap', not orph, 'no headline ends in a lone short line' if not orph else
        f'{len(orph)} headline(s) wrap into a short last line ("{orph[0][:24]}…") → text-wrap:balance on #cap, or shorter copy', warn=True)

def main():
    a = argparse.ArgumentParser(); a.add_argument('page'); a.add_argument('--lang', default='zh'); a.add_argument('--frames', type=int, default=24); a.add_argument('--aspect', choices=ASPECTS)
    o = a.parse_args(); res = []
    def add(name, ok, msg, warn=False): res.append((name, 'PASS' if ok else ('WARN' if warn else 'FAIL'), msg))
    with sync_playwright() as p:
        b, pg, _, _ = open_page(p, o.page, o.lang, wait=900, aspect=o.aspect)
        if not pg.evaluate('!!window.DEMO_CFG'):
            print('SKIP  not an engine page (window.DEMO_CFG missing — legacy inline renderer). Port it to templates/demo.html to get the'); print('      commercial layer (subtitles, callouts, clock, framing rules, declutter) and this check.'); sys.exit(2)
        C = pg.evaluate('''(()=>{const C=window.DEMO_CFG;return {dur:C.duration,caps:(C._caps||C.captions).map(c=>[c[0],c[1],c[3]||'']),
            subs:C.subtitles?C.subtitles.items.map(s=>[s.t0,s.t1]):null,sp:C.spotlight||null,spots:(C.spots||[]).length,cb:C.camBounds||null,
            mm:!!C.minimap,notes:(C.notes||[]).length,camIn:C.camIn||null,camOut:C.camOut||null,foot:!!(C.footage&&C.footage.length)}})()''')
        D = C['dur']
        # hook
        pg.evaluate('render(1.5)'); pg.wait_for_timeout(60)
        chars = pg.evaluate('''(()=>{let n=0;const w=document.createTreeWalker(document.querySelector('#stage'),NodeFilter.SHOW_TEXT);let nd;while(nd=w.nextNode()){const t=nd.textContent.trim();if(!t)continue;
            const e=nd.parentElement,r=e.getBoundingClientRect();if(r.width<2||r.bottom<0||r.top>innerHeight||r.right<0||r.left>innerWidth)continue;let x=e,op=1;while(x&&x!==document.body){op*=+getComputedStyle(x).opacity;x=x.parentElement;}if(op>0.5)n+=t.length;}return n})()''')
        add('hook', chars >= 6 or any(c[0] < 3 for c in C['caps']), f'{chars} readable chars at 1.5 s')
        add('length', 10 <= D <= 100, f'{D:.0f} s' + ('' if D <= 100 else ' — one storyline rarely needs > 90 s; offer a 60–90 s cut + 15–30 s social cut'), warn=D > 100)
        sc = sum(b_ - a_ for a_, b_ in C['subs']) / D if C['subs'] else 0
        add('subtitles', sc >= 0.35, f'cover {sc:.0%} of runtime' if C['subs'] else 'missing → subtitle_marks.py vo.tsv subs.json → <script src="subs.js"> (OK only for music-only films)', warn=not C['subs'])
        long = [c for c in C['caps'] if c[1] - c[0] > 3.5 and c[2] != 'hold']; cov = sum(c[1] - c[0] for c in C['caps']) / D
        add('headlines', not long and cov <= 0.55, f'{len(C["caps"])} cards, on screen {cov:.0%} of runtime' + (f', {len(long)} longer than 3.5 s' if long else ''))
        sp = C['sp'] or {}
        add('spotlight', (sp.get('dim', 0.35) <= 0.4 and sp.get('blur', 1.2) <= 1.6), f"dim {sp.get('dim', 'default 0.35')}, blur {sp.get('blur', 'default 1.2')}")
        qa = run([sys.executable, f'{S}/shot_qa.py', o.page, '--lang', o.lang, *(['--aspect', o.aspect] if o.aspect else [])]); m = re.search(r'(\d+) holds checked, (\d+) with issues', qa)
        cq = run([sys.executable, f'{S}/camera_qa.py', o.page, '--lang', o.lang, *(['--aspect', o.aspect] if o.aspect else [])]); m2 = re.search(r'reversals \(jitter\): (\d+)', cq)
        add('framing', bool(C['cb']) and not C['mm'] and m and m.group(2) == '0' and m2 and m2.group(1) == '0',
            f"camBounds={C['cb']}, minimap={'on' if C['mm'] else 'off'}, shot_qa {m.group(2) if m else '?'}/{m.group(1) if m else '?'} issues, jitter {m2.group(1) if m2 else '?'}")
        # sample frames
        lo, hi = (C['camIn'] or [3, 3])[1], (C['camOut'] or [D - 4])[0]
        ts = list(np.linspace(lo + 0.3, max(lo + 0.6, hi - 0.3), o.frames))
        maxover, overt, small, total, lum = 0, None, 0, 0, []
        for t in ts:
            pg.evaluate(f'render({t:.3f})'); pg.wait_for_timeout(40)
            n = pg.evaluate('''(sels)=>{let n=0;for(const q of sels)for(const e of document.querySelectorAll(q)){let x=e,op=1;while(x&&x!==document.body){op*=+getComputedStyle(x).opacity;x=x.parentElement;}
                const r=e.getBoundingClientRect();if(op>0.3&&r.width>4&&r.right>0&&r.left<innerWidth&&r.bottom>0&&r.top<innerHeight){n++;break;}}return n}''', OVER)
            if n > maxover: maxover, overt = n, t
            sz = pg.evaluate('''(()=>{let s=0,a=0;const W=document.querySelector('#win')||document.querySelector('#stage');for(const e of W.querySelectorAll('*')){if(e.children.length)continue;const t=(e.textContent||'').trim();if(!t)continue;
                const r=e.getBoundingClientRect();if(r.width<2||r.bottom<0||r.top>innerHeight||r.right<0||r.left>innerWidth)continue;if(e.tagName==='IMG')continue;let x=e,op=1;while(x&&x!==document.body){op*=+getComputedStyle(x).opacity;x=x.parentElement;}if(op<0.5)continue;
                const fs=parseFloat(getComputedStyle(e).fontSize),k=e.offsetHeight?r.height/e.offsetHeight:1,px=fs*k;a+=t.length;if(px<14)s+=t.length;}return [s,a]})()''')
            small += sz[0]; total += sz[1]
            png = pg.screenshot(); lum.append(np.asarray(Image.open(io.BytesIO(png)).convert('L')).mean())
        add('clutter', maxover <= 3, f'max {maxover} overlay layers at once' + (f' (t={overt:.1f}s)' if overt else ''))
        if total and not C['foot']:
            add('text size', small / total <= 0.3, f'{1 - small / total:.0%} of visible UI text ≥ 14 px on screen')
        elif C['foot']:
            add('text size', False, 'real footage: check recording zoom (125–150 % UI scale) by eye', warn=True)
        add('brightness', np.mean(lum) >= 30, f'mean luma {np.mean(lum):.1f}')
        # end card
        pg.evaluate(f'render({D - 0.8:.2f})'); pg.wait_for_timeout(60)
        ctas = pg.evaluate('''(re)=>{const R=new RegExp(re,'i');const seen=[];for(const e of document.querySelectorAll('#stage *')){if(e.children.length&&!e.className.toString().includes('cta'))continue;const t=(e.textContent||'').trim();
            if(!t||!R.test(t))continue;const r=e.getBoundingClientRect();if(r.width<2)continue;let x=e,op=1;while(x&&x!==document.body){op*=+getComputedStyle(x).opacity;x=x.parentElement;}if(op>0.5&&!seen.some(s=>s.includes(t)||t.includes(s)))seen.push(t);}return seen}''', CTA_RE)
        cur = pg.evaluate('''(()=>{for(const q of ['#cursor','#tcur']){const e=document.querySelector(q);if(e&&+getComputedStyle(e).opacity>0.1)return q}return null})()''')
        add('end card', len(ctas) == 1 and not cur, f'CTAs: {ctas or "none"}' + (f'; cursor {cur} visible on end card' if cur else ''), warn=len(ctas) > 1 and not cur)
        # end-card text stability: text that DRIFTS by < 0.5 px per frame (slow zoom/pan on a card) re-rasterises every frame and
        # visibly shimmers. Big moves (entrances) and zero moves (static) are fine. Subtitles are excluded.
        fps = pg.evaluate('window.FPS||30'); worst = (0, ''); hits = {}
        for t in np.linspace(D - 2.0, D - 0.2, 7):
            r = pg.evaluate(f'''(()=>{{const get=()=>{{const o=[];const w=document.createTreeWalker(document.querySelector('#stage'),NodeFilter.SHOW_TEXT);let nd;
                while(nd=w.nextNode()){{const e=nd.parentElement;if(!nd.textContent.trim()||e.closest('#subs'))continue;if(parseFloat(getComputedStyle(e).fontSize)<18)continue;
                let x=e,op=1;while(x&&x!==document.body){{op*=+getComputedStyle(x).opacity;x=x.parentElement;}}if(op<0.9)continue;const q=e.getBoundingClientRect();
                if(q.width>20&&q.top>0&&q.bottom<innerHeight)o.push([nd.textContent.trim().slice(0,24),q.left,q.top,q.width,q.height]);}}return o}};
                render({t:.4f});const a=get();render({t + 1 / fps:.4f});const b=get();const out=[];
                for(const A of a){{const B=b.find(x=>x[0]===A[0]);if(!B)continue;const d=Math.max(...[1,2,3,4].map(i=>Math.abs(A[i]-B[i])));out.push([A[0],d]);}}return out}})()''')
            for name, d in r:
                if 0.02 < d < 0.5: hits[name] = hits.get(name, 0) + 1; worst = max(worst, (d, name)) if hits[name] >= 3 else worst
        # sustained drift only (≥3 of 7 samples): the tail of an entrance ease-out is briefly sub-pixel and is fine
        add('end card stable', worst[0] == 0, 'no sub-pixel text drift in the last 2 s' if worst[0] == 0 else
            f'"{worst[1]}" drifts {worst[0]:.2f} px/frame → text shimmers; hold the card still after its entrance (no slow zoom/pan on text)')
        # establishing shot: first hold after the window lands should be on the bounds (wide) and last ≥ 1.2 s
        es = pg.evaluate('''(()=>{const C=DEMO_CFG,K=C.cam,B=C.camBounds;if(!K.length||!B)return null;const t0=C.camIn?C.camIn[1]:0;
            for(let i=0;i<K.length-1;i++){if(K[i+1][0]<=t0)continue;const same=JSON.stringify(K[i][1])===JSON.stringify(K[i+1][1]);
              if(same)return [K[i][1].includes(B),+(K[i+1][0]-Math.max(K[i][0],t0)).toFixed(2),K[i][1].join(',')];
              if(K[i][1].includes(B)&&!same)return [true,+(K[i+1][0]-Math.max(K[i][0],t0)).toFixed(2),K[i][1].join(',')];}return null})()''')
        if es:
            wide, hold, sel = es
            add('establish', wide and hold >= 1.2, f'first shot after camIn: {"wide" if wide else "close-up on " + sel}, {hold:g} s' +
                ('' if wide and hold >= 1.2 else ' → hold the wide shot (camBounds) ≥ 1.2–2 s before the first push-in'), warn=True)
        bs = pg.evaluate('''(()=>{const C=DEMO_CFG,B=C._beats;if(!B)return null;const K=C.cam,ts=[];
            for(let i=1;i<K.length;i++)if(JSON.stringify(K[i-1][1])!==JSON.stringify(K[i][1]))ts.push(K[i][0]);(C._caps||[]).forEach(c=>ts.push(c[0]));
            const on=ts.filter(t=>B.some(b=>Math.abs(b-t)<=0.06));return [on.length,ts.length,(C._beatLog||[]).length,(window.BEATS||{}).bpm||null]})()''')
        if bs is None: add('beat sync', False, 'no beat grid → scripts/beat_grid.py site/beats.js --bpm N | --wav music.wav (cuts land on the music)', warn=True)
        else:
            on, n, moved, bpm = bs
            add('beat sync', not n or on / n >= 0.6, f'{on}/{n} cuts on the beat ({bpm} BPM, {moved} snapped by the engine)' +
                ('' if not n or on / n >= 0.6 else ' → move keyframes closer to beats (> beatSnap.tol away) or raise beatSnap.tol'), warn=True)
        add('focus aids', D < 20 or C['notes'] > 0 or C['spots'] > 0 or bool(C['sp']), f"{C['notes']} callouts, {C['spots']} spots", warn=True)
        # hold stillness: camera transform constant inside each hold; text must not creep sub-pixel for long stretches
        ci, co = (C['camIn'] or [0, 0])[1], (C['camOut'] or [D])[0]    # the window entry / exit animate #cam on purpose
        holds = [(max(a_, ci), min(z_, co)) for a_, z_, hold in cam_segments(pg) if hold]
        holds = [(a_, z_) for a_, z_ in holds if z_ - a_ > 0.8]
        drift_cam, creep = [], []
        for a_, z_ in holds:
            ts_ = [k / 30 for k in range(int(a_ * 30) + 2, int(z_ * 30) - 1, 3)]
            # one round trip per hold: for each t → [camera transform, # text nodes moving sub-pixel between t and t+1 frame]
            r = pg.evaluate('''(ts)=>{const g=()=>{const o=[];const w=document.createTreeWalker(document.querySelector('#win')||document.querySelector('#stage'),NodeFilter.SHOW_TEXT);let n;
              while(n=w.nextNode()){if(!n.textContent.trim())continue;const r=document.createRange();r.selectNodeContents(n);const b=r.getBoundingClientRect();o.push(b.width?[b.left,b.top]:null)}return o};
              return ts.map(t=>{render(t);const tf=(document.querySelector('#cam')||{style:{}}).style.transform;const A=g();render(t+1/30);const B=g();let m=0;
              A.forEach((x,i)=>{const y=B[i];if(x&&y){const dd=Math.max(Math.abs(x[0]-y[0]),Math.abs(x[1]-y[1]));if(dd>0.02&&dd<0.6)m++;}});return [tf,m]})}''', ts_)
            streak = best = 0
            for _, m in r: streak = streak + 1 if m else 0; best = max(best, streak)
            if len({tf for tf, _ in r}) > 1: drift_cam.append(f'{a_:g}–{z_:g}s')
            if best >= 4: creep.append(f'{a_:g}–{z_:g}s')      # ≥ 4 consecutive samples (every 0.1 s) ≈ 0.4 s of creeping text
        still = not drift_cam and not creep
        add('hold still', still, f'{len(holds)} holds still' if still else
            (f'camera drifts in holds {", ".join(drift_cam)} (holdPush?) ' if drift_cam else '') + (f'text creeps sub-pixel in {", ".join(creep)} → slow float/lift or long ease tail on text; use H.reveal/H.settle, keep lifts shadow-only' if creep else ''))
        layout_checks(pg, D, add)
        # logo: any <img> whose bytes equal a shipped placeholder (templates/logo_t.png) → FAIL, unless this IS a template page
        srcs = pg.evaluate("[...document.querySelectorAll('img')].map(i=>decodeURIComponent(new URL(i.src).pathname))")
        md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest() if os.path.isfile(p) else None
        ph = md5(os.path.join(S, '..', 'templates', 'logo_t.png'))
        in_tpl = os.path.abspath(o.page).startswith(os.path.abspath(os.path.join(S, '..', 'templates')))
        bad = sorted({os.path.basename(x) for x in srcs if ph and md5(x) == ph}); ok = in_tpl or not bad
        add('logo', ok, ('template page (placeholder allowed)' if bad else 'no placeholder logo') if ok else f'{", ".join(bad)} is the template placeholder → use the real logo (scripts/app_logo.py "/Applications/<App>.app" site/ or logo_alpha.py)')
        # brand name: end-card title vs VO script
        pg.evaluate(f'render({D - 0.5:.2f})'); pg.wait_for_timeout(60)
        name = pg.evaluate('''(()=>{for(const q of ['#ename','#end .t1','#end h1','#end .name','#brand']){const e=document.querySelector(q);if(e&&e.textContent.trim())return e.textContent.trim()}return ''})()''')
        vo = os.path.join(os.path.dirname(os.path.abspath(o.page)), '..', f'vo_{o.lang}.tsv')
        if name and os.path.isfile(vo):
            txt = open(vo, encoding='utf-8').read(); hit = name.lower() in txt.lower()
            add('brand name', hit, f'"{name}" appears in the VO' if hit else f'end card says "{name}" but vo_{o.lang}.tsv never does → check the product name (renamed brand? typo?) on screen, in the VO and in the real UI', warn=True)
        b.close()
    w = max(len(r[0]) for r in res)
    for n, s, msg in res: print(f'{s:4}  {n:<{w}}  {msg}')
    sc = sum(r[1] == 'PASS' for r in res)
    print(f'\nscore {sc}/{len(res)} automatic checks passed')
    print('MANUAL  licensed music · natural/human VO · facts, numbers & brand review · disclaimer for simulated UI/data · 3–5 viewers on a phone')
    sys.exit(1 if any(r[1] == 'FAIL' for r in res) else 0)

if __name__ == '__main__':
    main()
