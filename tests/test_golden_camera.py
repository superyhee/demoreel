#!/usr/bin/env python3
"""Golden camera regression: the starter template's camera + cursor at key times, for every aspect.
Compares numbers (not pixels) so it holds across OSes and fonts. A framing change that is intended → --update and
review the diff of tests/golden/camera.json in the PR.
usage: python tests/test_golden_camera.py [--update]
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from page_util import open_page, ASPECTS
from playwright.sync_api import sync_playwright

PAGE = os.path.join(ROOT, 'templates', 'demo.html')
GOLD = os.path.join(HERE, 'golden', 'camera.json')
TIMES = [4.3, 5.5, 6.8, 8.1, 9.2, 11.4, 13.7, 14.6]   # camIn, wide hold, push-in, hold, move, hold+callout, camOut
TOL = {'px': 8.0, 'deg': 0.5, '': 0.01}   # px absolute (button size follows the font: Linux vs macOS ≈ 6 px), deg, scale relative

def nums(tf): return [(float(v), u) for v, u in re.findall(r'(-?\d+(?:\.\d+)?)(px|deg)?', tf or '')]

def capture():
    out = {}
    with sync_playwright() as p:
        for a in ASPECTS:
            b, pg, _, errs = open_page(p, PAGE, 'en', aspect=a)
            if errs: sys.exit(f'{a}: page error {errs[0]}')
            out[a] = {f'{t:g}': pg.evaluate(f"(render({t}),[document.querySelector('#cam').style.transform,"
                                             f"document.querySelector('#cursor').style.transform])") for t in TIMES}
            b.close()
    return out

def diff(gold, cur):
    bad = []
    for a, ts in gold.items():
        for t, (cam_g, cur_g) in ts.items():
            cam_c, cur_c = cur.get(a, {}).get(t, ['', ''])
            for what, g, c in (('camera', cam_g, cam_c), ('cursor', cur_g, cur_c)):
                G, Cn = nums(g), nums(c)
                if len(G) != len(Cn): bad.append(f'{a} {t}s {what}: {g!r} → {c!r}'); continue
                if any(abs(x - y) > TOL[u] * (abs(x) if not u else 1) for (x, u), (y, _) in zip(G, Cn)):
                    bad.append(f'{a} {t}s {what}: {g} → {c}')
    return bad

if __name__ == '__main__':
    cur = capture()
    if '--update' in sys.argv or not os.path.exists(GOLD):
        os.makedirs(os.path.dirname(GOLD), exist_ok=True)
        json.dump(cur, open(GOLD, 'w'), indent=1); print(f'wrote {GOLD}'); sys.exit(0)
    bad = diff(json.load(open(GOLD)), cur)
    if bad: print('camera regression:\n  ' + '\n  '.join(bad) + '\n(intended? python tests/test_golden_camera.py --update)'); sys.exit(1)
    print(f'ok: {len(ASPECTS)} aspects × {len(TIMES)} times match {os.path.relpath(GOLD, ROOT)}')
