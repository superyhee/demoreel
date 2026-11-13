#!/usr/bin/env python3
"""footage_events.build_map: cut plan (recording seconds) → engine footage map + speed badges. No video needed."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from footage_events import build_map

m, b, end = build_map([{'play': [2.6, 3.8], 'speed': 2}, {'hold': 5.85, 'dur': 2.0}, {'play': [6.9, 12.8], 'dur': 1.4}], 15.0)
assert m == [[15.0, 2.6], [15.6, 3.8], [15.601, 5.85], [17.6, 5.85], [17.601, 6.9], [19.0, 12.8]], m
assert b == [[15.0, 15.6, 2], [17.6, 19.0, 4]], b      # holds get no badge; 5.9 s in 1.4 s → ×4
assert end == 19.0, end
assert all(m[i][0] < m[i + 1][0] for i in range(len(m) - 1)), 'project time strictly increasing (1 ms cuts)'
m, b, _ = build_map([{'play': [0, 1], 'speed': 1.2}], 0)
assert b == [], 'no badge below 1.5×'
print('ok: footage map / badges from a cut plan')
