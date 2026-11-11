#!/usr/bin/env python3
"""Final deliverable check — run on every exported MP4 before handing it over (replaces ad-hoc ffprobe/ffmpeg poking).
usage: final_check.py final.mp4 [--page site/index.html --lang zh] [--times 3.3,9.2,…] [--tile out.png] [--dur 30]
Checks: container/stream (h264 1920×1080, audio present), duration (= page duration ±0.1 s), true peak ≤ −1 dBTP,
integrated loudness −16 ±2 LUFS, no black stretches ≥ 0.25 s outside intro/outro, and writes a labelled contact sheet of the
frames at TRANSITIONS (camera moves, camIn/camOut from the page — where glitches hide) → Read it.
Exit 1 on any FAIL."""
import argparse, json, os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw

def sh(cmd): return subprocess.run(cmd, capture_output=True, text=True)

def page_times(page, lang):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome'); pg = b.new_page(viewport={'width': 1920, 'height': 1080})
        pg.goto('file://' + os.path.abspath(page) + f'?lang={lang}'); pg.wait_for_timeout(800)
        c = pg.evaluate('''(()=>{const C=window.DEMO_CFG||{};return {d:C.duration||null,cam:(C.cam||[]).map(k=>[k[0],JSON.stringify(k[1])]),ci:C.camIn||null,co:C.camOut||null}})()''')
        b.close()
    ts = []
    if c['ci']: ts.append(c['ci'][1] - 0.15)
    cam = c['cam']
    for (t0, s0), (t1, s1) in zip(cam, cam[1:]):
        if s0 != s1: ts.append(round((t0 + t1) / 2, 2))          # middle of a move between different targets
    if c['co']: ts.append(sum(c['co']) / 2)
    return c['d'], ts

def main():
    a = argparse.ArgumentParser(); a.add_argument('mp4'); a.add_argument('--page'); a.add_argument('--lang', default='zh')
    a.add_argument('--times'); a.add_argument('--tile'); a.add_argument('--dur', type=float); o = a.parse_args(); res = []
    add = lambda n, ok, m: res.append((n, 'PASS' if ok else 'FAIL', m))
    pr = json.loads(sh(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', o.mp4]).stdout or '{}')
    if not pr.get('streams'): sys.exit(f'cannot read {o.mp4}')
    v = next((s for s in pr['streams'] if s['codec_type'] == 'video'), {}); au = [s for s in pr['streams'] if s['codec_type'] == 'audio']
    dur = float(pr['format']['duration'])
    add('streams', v.get('codec_name') == 'h264' and v.get('width') == 1920 and v.get('height') == 1080 and bool(au),
        f"{v.get('codec_name')} {v.get('width')}×{v.get('height')} {v.get('r_frame_rate')} · audio: {au[0]['codec_name'] if au else 'MISSING'}")
    pdur, ts = (page_times(o.page, o.lang) if o.page else (None, []))
    want = o.dur or pdur
    add('duration', want is None or abs(dur - want) <= 0.1, f'{dur:.2f} s' + (f' (page {want:g} s)' if want else ''))
    if au:
        ld = sh(['ffmpeg', '-hide_banner', '-nostats', '-i', o.mp4, '-af', 'ebur128=peak=true', '-f', 'null', '-']).stderr
        I = re.findall(r'I:\s+(-?[\d.]+) LUFS', ld); TP = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', ld)
        if I: add('loudness', abs(float(I[-1]) + 16) <= 2, f'{float(I[-1]):.1f} LUFS integrated (target −16 ±2)')
        if TP: add('true peak', float(TP[-1]) <= -1.0, f'{float(TP[-1]):.1f} dBTP (≤ −1)')
    bl = sh(['ffmpeg', '-hide_banner', '-i', o.mp4, '-vf', 'blackdetect=d=0.25:pix_th=0.06', '-an', '-f', 'null', '-']).stderr
    blk = [(float(s), float(e)) for s, e in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', bl)]
    mid = [b for b in blk if b[0] > 0.3 and b[1] < dur - 0.3]
    add('black frames', not mid, 'none' if not mid else ', '.join(f'{s:.2f}–{e:.2f}s' for s, e in mid))
    if o.times: ts = [float(x) for x in o.times.split(',')]
    if not ts: ts = [round(dur * k / 9, 2) for k in range(1, 9)]
    ts = sorted({round(t, 2) for t in ts if 0 <= t < dur})[:12]
    tile = o.tile or os.path.splitext(o.mp4)[0] + '_check.png'; d = tempfile.mkdtemp(); ims = []
    for t in ts:
        f = os.path.join(d, f'{t:.2f}.png'); sh(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', o.mp4, '-frames:v', '1', f])
        if os.path.exists(f):
            im = Image.open(f).convert('RGB').resize((640, 360)); ImageDraw.Draw(im).rectangle((0, 0, 92, 26), fill=(0, 0, 0))
            ImageDraw.Draw(im).text((8, 6), f'{t:.2f}s', fill=(255, 255, 255)); ims.append(im)
    if ims:
        cols = 3; rows = (len(ims) + cols - 1) // cols; sheet = Image.new('RGB', (640 * cols, 360 * rows), (255, 255, 255))
        for i, im in enumerate(ims): sheet.paste(im, ((i % cols) * 640, (i // cols) * 360))
        sheet.save(tile)
    w = max(len(r[0]) for r in res)
    for n, s, m in res: print(f'{s:4}  {n:<{w}}  {m}')
    print(f'transition sheet ({len(ims)} frames at {", ".join(f"{t:g}" for t in ts)}) → {tile}   ← Read it')
    sys.exit(1 if any(r[1] == 'FAIL' for r in res) else 0)

if __name__ == '__main__': main()
