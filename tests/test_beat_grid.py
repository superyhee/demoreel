#!/usr/bin/env python3
"""Beat detection regression: render a procedural score (known grid) and check tempo + phase. usage: python tests/test_beat_grid.py"""
import json, os, subprocess, sys, tempfile
import numpy as np
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts')
d = tempfile.mkdtemp(); wav, js = os.path.join(d, 'm.wav'), os.path.join(d, 'b.js')
subprocess.run([sys.executable, f'{S}/music_styles.py', wav, '--style', 'electronic', '--dur', '20', '--main', '7', '--lift', '15',
                '--peak', '16', '--drop', '18', '--end', '18.5'], check=True, capture_output=True)
subprocess.run([sys.executable, f'{S}/beat_grid.py', js, '--wav', wav], check=True)
B = json.loads(open(js).read()[len('window.BEATS='):-2]); t = np.array(B['beats']); t = t[(t > 6) & (t < 17)]
err = np.array([np.min(np.abs(np.arange(0, 20, 0.5) - x)) for x in t])
print(f"bpm {B['bpm']}  median phase error {np.median(err) * 1000:.0f} ms  max {err.max() * 1000:.0f} ms")
assert abs(B['bpm'] - 120) < 1, B['bpm']
assert np.median(err) < 0.03 and err.max() < 0.06, err
print('ok')
