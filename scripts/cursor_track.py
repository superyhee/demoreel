#!/usr/bin/env python3
"""Track (and optionally erase) the real mouse pointer in screen-recording footage, so the engine can draw a large,
smooth Screen-Studio-style cursor on the same path (engine option `cursorTrack`).

usage:
  # 1) cut templates once per recording scale (frame with the pointer, frame without it, approx hotspot, kind)
  cursor_track.py cut rec/ tpl/ --sample 60:933,831:arrow:110 --sample 150:1410,540:hand:200 --sample 215:1595,1041:ibeam:190
  #    (or reuse the shipped macOS templates: assets/cursors/ at 1.27 px/pt, add --scale <your px/pt / 1.27>)
  # 2) track every frame → JSON [[frameIdx, x, y, kind] | [frameIdx, null]]   (footage px, x/y = pointer HOTSPOT)
  cursor_track.py track rec/ tpl/ cursor.json [--workers 8] [--thr 0.12]
  # 3) erase the real pointer from the frames (in place, keeps a backup dir) so only the engine cursor is visible
  cursor_track.py erase rec/ tpl/ cursor.json [--backup rec_orig/]

Frames: rec/f00001.jpg … (footage_prep.py layout). Templates: <kind>.png (gray) + <kind>_m.png (mask) + tpl.json (hotspots, optional per-kind 'thr').
Cut separate templates for light and dark backgrounds (macOS I-beam has no visible outline on white: kind 'ibeamL').
Small/thin templates (I-beam) need a stricter per-kind thr (≈0.04) or they match static glyphs.
Detection = masked SQDIFF template matching, searched near the previous hit first, full frame on miss.
Erase = copy the pointer area from the nearest frame where the pointer is elsewhere and the surrounding ring matches\n(seamless on text/buttons); cv2.inpaint only as a fallback. Originals are read from --backup, so erase is re-runnable.
"""
import argparse, json, os, sys, glob
import numpy as np, cv2
from concurrent.futures import ProcessPoolExecutor

def frames(d): return sorted(glob.glob(os.path.join(d, 'f*.jpg')) + glob.glob(os.path.join(d, 'f*.png')))
def gray(p): return cv2.imread(p, cv2.IMREAD_GRAYSCALE)
def idx(p): return int(os.path.basename(p)[1:].split('.')[0])

def cut(o):
    os.makedirs(o.tpl, exist_ok=True); meta = {}
    F = {idx(p): p for p in frames(o.rec)}
    for s in o.sample:
        fr, xy, kind, clean = s.split(':'); x, y = map(int, xy.split(',')); r = 22
        a = gray(F[int(fr)]).astype(int); b = gray(F[int(clean)]).astype(int)
        A = a[y - r:y + r, x - r:x + r]; d = np.abs(A - b[y - r:y + r, x - r:x + r]) > 35
        d = cv2.morphologyEx(d.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(d)
        k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))         # biggest blob = the pointer
        ys, xs = np.nonzero(lab == k); x0, x1, y0, y1 = xs.min() - 1, xs.max() + 2, ys.min() - 1, ys.max() + 2
        m = (lab[y0:y1, x0:x1] == k).astype(np.uint8) * 255   # exact glyph+outline, no background (else misses on light UIs)
        cv2.imwrite(f'{o.tpl}/{kind}.png', A[y0:y1, x0:x1].astype(np.uint8)); cv2.imwrite(f'{o.tpl}/{kind}_m.png', m)
        H, W = m.shape
        hs = (1, 1) if kind == 'arrow' else (W // 2, H // 2)
        if kind == 'hand':   # fingertip = topmost mask pixel
            yy, xx = np.nonzero(m); i = int(np.argmin(yy)); hs = (int(xx[i]), int(yy[i]))
        meta[kind] = {'hot': hs, 'size': [W, H]}; print(kind, 'template', W, 'x', H, 'hotspot', hs)
    json.dump(meta, open(f'{o.tpl}/tpl.json', 'w'))

def load_tpl(d, scale=1.0):
    meta = json.load(open(f'{d}/tpl.json')); T = {}
    for k, v in meta.items():
        g = cv2.imread(f'{d}/{k}.png', 0); m = cv2.imread(f'{d}/{k}_m.png', 0)
        if scale != 1: g = cv2.resize(g, None, fx=scale, fy=scale); m = cv2.resize(m, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        T[k] = (g.astype(np.float32), (m > 0).astype(np.float32), [round(c * scale) for c in v['hot']], v.get('thr'))
    return T

def match(img, T, thr, near=None, R=160):
    best = None
    for k, (g, m, hot, kt) in T.items():
        h, w = g.shape; ox = oy = 0; sub = img
        if near:
            ox, oy = max(0, near[0] - R), max(0, near[1] - R); sub = img[oy:near[1] + R, ox:near[0] + R]
            if sub.shape[0] < h or sub.shape[1] < w: continue
        res = cv2.matchTemplate(sub, g, cv2.TM_SQDIFF, mask=m) / (m.sum() * 255.0 ** 2)
        v, _, loc, _ = cv2.minMaxLoc(res)
        if v < min(thr, kt or 1) and (best is None or v < best[0]): best = (v, k, loc[0] + ox + hot[0], loc[1] + oy + hot[1])
    return best

def track_chunk(args):
    paths, tpl, thr, scale = args; T = load_tpl(tpl, scale); out = []; prev = None
    for p in paths:
        img = gray(p).astype(np.float32)
        b = match(img, T, thr, near=prev) if prev else None
        if not b: b = match(img, T, thr)
        if b: prev = (b[2], b[3]); out.append([idx(p), b[2], b[3], b[1], round(b[0], 4)])
        else: prev = None; out.append([idx(p), None])
    return out

def track(o):
    P = frames(o.rec); n = max(1, o.workers); ch = [P[i * len(P) // n:(i + 1) * len(P) // n] for i in range(n)]
    with ProcessPoolExecutor(n) as ex: res = sum(ex.map(track_chunk, [(c, o.tpl, o.thr, o.scale) for c in ch]), [])
    # despeckle: drop isolated single-frame hits / fill single-frame misses
    for i in range(1, len(res) - 1):
        a, b, c = res[i - 1], res[i], res[i + 1]
        if b[1] is None and a[1] is not None and c[1] is not None and abs(a[1] - c[1]) + abs(a[2] - c[2]) < 30: res[i] = [b[0], a[1], a[2], a[3], a[4]]
        elif b[1] is not None and a[1] is None and c[1] is None and b[4] > 0.03: res[i] = [b[0], None]   # weak isolated hit
    json.dump(res, open(o.out, 'w'))
    hit = sum(r[1] is not None for r in res); print(f'{hit}/{len(res)} frames with a pointer -> {o.out}')

def pointer_mask(T, k, x, y, H, W, pad):
    g, m, hot, _ = T[k]; h, w = m.shape; M = np.zeros((H, W), np.uint8); x0, y0 = x - hot[0], y - hot[1]
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return None
    M[ya:yb, xa:xb] = (m[ya - y0:yb - y0, xa - x0:xb - x0] * 255).astype(np.uint8)
    return cv2.dilate(M, np.ones((pad, pad), np.uint8))

def erase_chunk(args):
    items, tpl, scale, src, pad, trk, win, tol = args; T = load_tpl(tpl, scale); stats = [0, 0]
    pos = {r[0]: r for r in trk}
    for p, i, (x, y, k) in items:
        img = cv2.imread(os.path.join(src, os.path.basename(p))); H, W = img.shape[:2]
        M = pointer_mask(T, k, x, y, H, W, pad)
        if M is None: continue
        ring = cv2.dilate(M, np.ones((9, 9), np.uint8)) & ~M; R = ring > 0; done = False
        # temporal patch: nearest frame where the pointer is elsewhere and the surroundings match
        for d in range(1, win + 1):
            for j in (i - d, i + d):
                r = pos.get(j)
                if r is None: continue
                if r[1] is not None and abs(r[1] - x) + abs(r[2] - y) < 50: continue
                dp = os.path.join(src, f'f{j:05d}.jpg')
                if not os.path.exists(dp): continue
                don = cv2.imread(dp)
                if np.abs(don[R].astype(int) - img[R].astype(int)).mean() > tol: continue
                img[M > 0] = don[M > 0]; done = True; break
            if done: break
        if not done: img = cv2.inpaint(img, M, 5, cv2.INPAINT_TELEA)
        stats[0 if done else 1] += 1
        cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return stats

def erase(o):
    import shutil
    tr = json.load(open(o.track)); F = {idx(p): p for p in frames(o.rec)}
    if not o.backup: sys.exit('--backup DIR is required (originals are read from it)')
    if not os.path.exists(o.backup): shutil.copytree(o.rec, o.backup)
    items = [(F[r[0]], r[0], (r[1], r[2], r[3])) for r in tr if r[1] is not None and r[0] in F]
    n = max(1, o.workers); ch = [items[i::n] for i in range(n)]
    with ProcessPoolExecutor(n) as ex: st = list(ex.map(erase_chunk, [(c, o.tpl, o.scale, o.backup, o.pad, tr, o.win, o.tol) for c in ch]))
    print(f'erased pointer in {len(items)} frames: {sum(a for a, b in st)} temporal patches, {sum(b for a, b in st)} inpainted (originals: {o.backup})')

if __name__ == '__main__':
    a = argparse.ArgumentParser(); s = a.add_subparsers(dest='cmd', required=True)
    c = s.add_parser('cut'); c.add_argument('rec'); c.add_argument('tpl'); c.add_argument('--sample', action='append', required=True)
    t = s.add_parser('track'); t.add_argument('rec'); t.add_argument('tpl'); t.add_argument('out')
    e = s.add_parser('erase'); e.add_argument('rec'); e.add_argument('tpl'); e.add_argument('track'); e.add_argument('--backup'); e.add_argument('--pad', type=int, default=5); e.add_argument('--win', type=int, default=90); e.add_argument('--tol', type=float, default=6)
    for p in (t, e): p.add_argument('--workers', type=int, default=8); p.add_argument('--scale', type=float, default=1.0)
    t.add_argument('--thr', type=float, default=0.12)
    o = a.parse_args(); {'cut': cut, 'track': track, 'erase': erase}[o.cmd](o)
