#!/usr/bin/env python3
"""Use a real UI sound library (e.g. Kenney CC0 packs) instead of synthesized SFX.

  sfx_lib.py index ~/Downloads/kenney lib.json        # scan .ogg/.wav, rank candidates per SFX type → lib.json
  sfx_lib.py audition lib.json audition/              # one wav per type: candidates 0.8 s apart + audition/README.txt (order)
  edit lib.json "pick": the files you liked (default = top 3 per type), then
  sfx.py sfx.json sfx.wav 30 --lib lib.json           # library samples, level-matched to the synthesized defaults

Types: click tick pop chime shimmer boom whoosh swish suck (engine SFX vocabulary). Types without candidates fall back to synthesis.
Selection = filename rules (what the sound IS) + features (duration, attack, brightness): product-demo sounds must be short, soft,
physical (keys, glass, wood) — avoid game bleeps (laser, powerUp, zap, phaser) and anything > 1.2 s except shimmer/boom.
Library licence: keep the pack's License.txt next to the files (Kenney = CC0, commercial use, no attribution required).
"""
import sys, os, json, glob, re, subprocess
import numpy as np

SR = 44100
RULES = {   # type: (filename regex, duration range s, prefer brightness Hz)
    'click':   (r'(^|/)(click|select|mouseclick)', (0.02, 0.25), 2500),
    'tick':    (r'(^|/)(tick|switch\d|scratch)', (0.01, 0.12), 3500),
    'pop':     (r'(^|/)(drop|pluck|bong|toggle)', (0.04, 0.45), 1200),
    'chime':   (r'(^|/)(confirmation|glass)', (0.15, 1.4), 2500),
    'shimmer': (r'(^|/)(jingles_(steel|pizzi)|glass|confirmation)', (0.5, 2.6), 3000),
    'boom':    (r'(^|/)(impactsoft_heavy|impactpunch_heavy|impactbell_heavy)', (0.2, 1.6), 300),
    'whoosh':  (r'(^|/)(maximize|minimize)', (0.15, 0.9), 1500),
    'swish':   (r'(^|/)(maximize|minimize|open|close)', (0.08, 0.5), 2000),
    'suck':    (r'(^|/)(minimize)', (0.15, 0.9), 1200),
}
AVOID = r'(laser|powerup|zap|phaser|spacetrash|pepsound|error|glitch|footstep|mining|question|jingles_(nes|sax|hit))'

def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(float)
    nz = np.nonzero(np.abs(x) > 1e-3)[0]
    return x[nz[0]:nz[-1] + 1] if len(nz) else x

def feats(x):
    d = len(x) / SR; pk = np.abs(x).max() + 1e-9; i = int(np.argmax(np.abs(x) > 0.5 * pk))
    sp = np.abs(np.fft.rfft(x[:min(len(x), SR // 2)] * np.hanning(min(len(x), SR // 2))))
    f = np.fft.rfftfreq(min(len(x), SR // 2), 1 / SR); cen = float((sp * f).sum() / (sp.sum() + 1e-9))
    return {'dur': round(d, 3), 'attack_ms': round(i / SR * 1000, 1), 'centroid': round(cen), 'peak': round(float(pk), 3)}

def index(root, out):
    files = sorted(glob.glob(os.path.join(os.path.expanduser(root), '**', '*.ogg'), recursive=True) +
                   glob.glob(os.path.join(os.path.expanduser(root), '**', '*.wav'), recursive=True))
    lib = {'root': os.path.expanduser(root), 'types': {}}
    F = {}
    for p in files:
        n = os.path.relpath(p, lib['root']).lower()
        if re.search(AVOID, n) or 'preview' in n: continue
        F[p] = feats(load(p))
    for ty, (rx, (d0, d1), bright) in RULES.items():
        c = []
        for p, f in F.items():
            n = os.path.relpath(p, lib['root']).lower()
            if not re.search(rx, n) or not (d0 <= f['dur'] <= d1): continue
            # score: crisp attack, brightness near target, shorter is better for UI types
            s = -abs(np.log((f['centroid'] + 50) / bright)) - f['attack_ms'] / 40 - (f['dur'] / d1) * (0.6 if ty in ('click', 'tick', 'pop') else 0.1)
            c.append((round(s, 3), p, f))
        c.sort(key=lambda z: -z[0])
        lib['types'][ty] = {'candidates': [{'file': p, **f, 'score': s} for s, p, f in c[:8]], 'pick': [p for _, p, _ in c[:3]]}
        print(f'{ty:8} {len(c):3} candidates' + (f'  top: {os.path.basename(c[0][1])}' if c else '  (none → synthesized)'))
    json.dump(lib, open(out, 'w'), indent=1); print('→', out)

def audition(libf, outdir):
    lib = json.load(open(libf)); os.makedirs(outdir, exist_ok=True); notes = []
    import wave
    for ty, v in lib['types'].items():
        if not v['candidates']: continue
        seq = []
        for i, c in enumerate(v['candidates']):
            x = load(c['file']); x = x / (np.abs(x).max() + 1e-9) * 0.5; seq += [x, np.zeros(int(SR * 0.8))]
            notes.append(f'{ty}  #{i + 1}  {os.path.relpath(c["file"], lib["root"])}  ({c["dur"]} s)')
        y = (np.concatenate(seq) * 32767).astype(np.int16)
        w = wave.open(os.path.join(outdir, f'{ty}.wav'), 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes()); w.close()
    open(os.path.join(outdir, 'README.txt'), 'w').write('\n'.join(notes) + '\n'); print('audition →', outdir)

if __name__ == '__main__':
    {'index': lambda: index(sys.argv[2], sys.argv[3]), 'audition': lambda: audition(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
