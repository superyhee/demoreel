#!/usr/bin/env python3
"""visual_review: previous-round loading (frames from frames.json or an older rubric.md) and the comparison report. No API."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from visual_review import load_prev, compare_md, RUBRIC

d = tempfile.mkdtemp()
open(os.path.join(d, 'rubric.md'), 'w').write('# x\n\n- #00 0.80s — hook — `frames/00.jpg`\n- #01 5.75s — establish + hold — `frames/01.jpg`\n')
sc = [{'key': k, 'score': 2, 'frames': [], 'evidence': 'fine', 'fix': ''} for k, _ in RUBRIC]
sc[3] = {'key': 'framing', 'score': 0, 'frames': ['#08'], 'evidence': 'FAIL box leaves the frame', 'fix': 'shrink the box'}
json.dump({'scores': sc, 'top_fixes': [], 'overall': ''}, open(os.path.join(d, 'review.json'), 'w'))
P = load_prev(d)
assert P['frames'] == [(0.8, 'hook'), (5.75, 'establish + hold')], P['frames']
assert P['issues'] == ['framing: FAIL box leaves the frame'], P['issues']          # the problem, not the fix
now = [dict(s) for s in sc]; now[3] = dict(sc[3], score=2)
r = {'scores': now, 'previous': [{'n': 1, 'status': 'fixed', 'evidence': 'box inside the frame in #08'}],
     'issues': [{'title': 'cursor covers the button', 'key': 'collisions', 'frames': ['#00'], 'prev': 0}]}
md = compare_md(r, P)
assert '**18 → 20**' in md and '| framing | 0 | 2 ▲ |' in md, md
assert '**Fixed** (1)' in md and 'box inside the frame' in md and '**New** (1)' in md and 'cursor covers the button' in md, md
print('ok: previous round + comparison report')
