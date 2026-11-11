#!/usr/bin/env python3
"""Extract the REAL product logo from an installed app bundle (never redraw it, never reuse templates/logo_t.png — that is a
placeholder for a fictional product).
usage: app_logo.py "/Applications/<App>.app" site/            → site/app_icon.png (512 px, the app icon as shipped)
                                                                 site/logo_glyph.png (512 px, transparent mark, if the icon is
                                                                 a light glyph on a coloured tile — recoloured with the tile's own gradient)
macOS: icon from Contents/Resources/*.icns via sips. Windows/Linux: pass a .png/.ico/.svg-rendered png path instead of the .app.
Check both outputs visually; for in-app marks that differ from the app icon, crop a screenshot with logo_alpha.py instead."""
import sys, os, glob, subprocess, plistlib, tempfile
import numpy as np
from PIL import Image
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
if src.endswith('.app'):
    res = os.path.join(src, 'Contents', 'Resources'); name = None
    try: name = plistlib.load(open(os.path.join(src, 'Contents', 'Info.plist'), 'rb')).get('CFBundleIconFile')
    except Exception: pass
    cands = [os.path.join(res, name if name.endswith('.icns') else name + '.icns')] if name else []
    cands = [c for c in cands if os.path.exists(c)] or sorted(glob.glob(os.path.join(res, '*.icns')), key=os.path.getsize, reverse=True)
    if not cands: sys.exit(f'no .icns in {res}')
    png = os.path.join(tempfile.mkdtemp(), 'icon.png')
    subprocess.run(['sips', '-s', 'format', 'png', cands[0], '--out', png], check=True, capture_output=True); src = png
im = Image.open(src).convert('RGBA'); a = np.asarray(im).astype(float)
ys, xs = np.nonzero(a[..., 3] > 8); bb = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)   # trim the transparent margin of the icns
icon = im.crop(bb); icon.resize((512, 512), Image.LANCZOS).save(os.path.join(out, 'app_icon.png'))
t = np.asarray(icon.resize((1024, 1024), Image.LANCZOS)).astype(float); rgb, al = t[..., :3], t[..., 3] / 255
light = np.clip((rgb.min(2) - 60) / 195, 0, 1) * al                    # white/light glyph
tile = (al > 0.9) & (light < 0.05)
if light.sum() < 1000 or tile.sum() < 1000: print('app_icon.png written; icon is not a light glyph on a tile → no glyph logo'); sys.exit()
# recolour with the tile's own colour field: per-pixel colour from a coarse grid of tile colours (keeps the brand gradient)
g = 16; H = W = 1024; col = np.zeros((g, g, 3)); cell = H // g
for i in range(g):
    for j in range(g):
        m = tile[i*cell:(i+1)*cell, j*cell:(j+1)*cell]
        col[i, j] = rgb[i*cell:(i+1)*cell, j*cell:(j+1)*cell][m].mean(0) if m.sum() > 20 else np.nan
for _ in range(g):                                                     # fill cells covered by the glyph from neighbours
    nan = np.isnan(col[..., 0])
    if not nan.any(): break
    pad = np.pad(col, ((1, 1), (1, 1), (0, 0)), constant_values=np.nan); nb = np.stack([pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]])
    fill = np.nanmean(nb, 0); col[nan] = fill[nan]
col = np.nan_to_num(col, nan=128); field = np.asarray(Image.fromarray(col.astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(float)
glyph = np.dstack([field, light * 255]).astype(np.uint8)
ys, xs = np.nonzero(light > 0.05); s = max(xs.max() - xs.min(), ys.max() - ys.min()); cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2; h = s / 2 * 1.07
Image.fromarray(glyph).crop((int(cx - h), int(cy - h), int(cx + h), int(cy + h))).resize((512, 512), Image.LANCZOS).save(os.path.join(out, 'logo_glyph.png'))
print('wrote app_icon.png + logo_glyph.png → use app_icon for hero/end cards, logo_glyph for in-UI marks (sidebar, avatar)')
