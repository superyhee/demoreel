#!/usr/bin/env python3
"""Footage post-production helper: the exact measuring is done here, the choices are yours (the agent reads the sheet).

  scan <rec.mp4> <out_dir> [--fps 10] [--thr 0.05] [--no-ocr]
      → out_dir/events.json + out_dir/events_sheet.png. Activity windows (frame difference), the SETTLED frame after each
        (what the viewer reads), and macOS Vision OCR of every settled frame: text lines with boxes in footage px.
  find <out_dir> "FAIL" [--at 5.9] [--row] [--below 1] [--pad 6]
      → hotspot / callout boxes [x,y,w,h] (footage px) of the OCR lines containing the text (nearest settled frame to --at).
  map <plan.json> [--start 15.0]
      → the footage `map` + `badges` for Demo.init, from a cut plan in recording seconds. Plan items, in film order:
          {"play":[a,b], "speed":2}   play recording a→b at 2× (badge ⏩×2 when speed ≥ 1.5)
          {"play":[a,b], "dur":1.2}   … or fit it into 1.2 s
          {"hold":t, "dur":2.0}       freeze on recording time t (read the result)
        Consecutive items are joined by a 1 ms cut, so idle waits between commands simply disappear.

Typical loop: scan → Read events_sheet.png → write plan.json (which windows to play / speed / hold) → map → find boxes for
the lines worth a callout. Uses ffmpeg, numpy, PIL; OCR needs macOS (Vision, compiled once with swiftc into ~/.cache/demoreel).
"""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

OCR_SWIFT = r'''
import Foundation
import Vision
import AppKit
var out: [[String: Any]] = []
for path in CommandLine.arguments.dropFirst() {
  guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { out.append(["file": path, "lines": []]); continue }
  let W = Double(cg.width), H = Double(cg.height)
  let req = VNRecognizeTextRequest(); req.recognitionLevel = .accurate; req.usesLanguageCorrection = false
  req.recognitionLanguages = ["en-US", "zh-Hans"]
  try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
  var lines: [[String: Any]] = []
  for o in req.results ?? [] { guard let c = o.topCandidates(1).first else { continue }; let b = o.boundingBox
    lines.append(["text": c.string, "conf": Double(c.confidence),
                  "box": [Int(b.minX * W), Int((1 - b.maxY) * H), Int(b.width * W), Int(b.height * H)]]) }
  out.append(["file": path, "lines": lines])
}
let d = try! JSONSerialization.data(withJSONObject: out, options: [])
FileHandle.standardOutput.write(d)
'''

def ocr_bin():
    b = os.path.expanduser('~/.cache/demoreel/vision_ocr')
    if not os.path.exists(b):
        os.makedirs(os.path.dirname(b), exist_ok=True); src = b + '.swift'; open(src, 'w').write(OCR_SWIFT)
        r = subprocess.run(['swiftc', '-O', src, '-o', b], capture_output=True, text=True)
        if r.returncode: sys.exit('vision_ocr: swiftc failed (Xcode command line tools?)\n' + r.stderr[-800:])
    return b

def probe(src):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration',
                        '-of', 'json', src], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout); s = j['streams'][0]; return s['width'], s['height'], float(j['format']['duration'])

def activity(src, fps, thr):
    """mean |Δ| between consecutive downscaled gray frames → merged activity windows [t0, t1] (s)"""
    W, Hh = 320, 180
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vf', f'fps={fps},scale={W}:{Hh},format=gray', '-f', 'rawvideo', '-'],
                         capture_output=True, check=True).stdout
    F = np.frombuffer(raw, np.uint8).reshape(-1, Hh, W).astype(np.int16)
    d = np.abs(np.diff(F, axis=0)).mean(axis=(1, 2))
    ev = []
    for i, x in enumerate(d, 1):
        if x <= thr: continue
        t = i / fps
        if ev and t - ev[-1][1] <= 2.5 / fps: ev[-1][1] = t
        else: ev.append([t - 1 / fps, t])
    return [[round(a, 2), round(b, 2)] for a, b in ev], len(F) / fps

def grab(src, t, path):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', src, '-frames:v', '1', path], check=True)

def scan(o):
    os.makedirs(o.out, exist_ok=True); W, Hh, dur = probe(o.src)
    ev, _ = activity(o.src, o.fps, o.thr); events = []
    for i, (a, b) in enumerate(ev):
        nxt = ev[i + 1][0] if i + 1 < len(ev) else dur
        settle = round(min(b + 0.15, (b + nxt) / 2, dur - 0.05), 2)
        f = os.path.join(o.out, f'settle_{i:02d}.png'); grab(o.src, settle, f)
        events.append({'i': i, 't0': a, 't1': b, 'settle': settle, 'frame': os.path.basename(f), 'kind': 'typing/stream' if b - a > 0.6 else 'burst'})
    if not o.no_ocr and sys.platform == 'darwin' and events:
        res = json.loads(subprocess.run([ocr_bin()] + [os.path.join(o.out, e['frame']) for e in events], capture_output=True, check=True).stdout)
        for e, r in zip(events, res): e['lines'] = r['lines']
    json.dump({'src': os.path.abspath(o.src), 'w': W, 'h': Hh, 'duration': round(dur, 3), 'events': events},
              open(os.path.join(o.out, 'events.json'), 'w'), ensure_ascii=False, indent=1)
    # contact sheet: one settled frame per event, labelled with its window
    tw, cols = 640, 3; tiles = []
    for e in events:
        im = Image.open(os.path.join(o.out, e['frame'])).convert('RGB'); im = im.resize((tw, round(tw * im.height / im.width)))
        d = ImageDraw.Draw(im); lab = f"#{e['i']:02d}  {e['t0']:.1f}–{e['t1']:.1f}s → settled {e['settle']:.2f}s  ({e['kind']})"
        d.rectangle((0, 0, 9 + 7 * len(lab), 22), fill=(0, 0, 0)); d.text((5, 5), lab, fill=(255, 255, 0)); tiles.append(im)
    if tiles:
        th = max(t.height for t in tiles); rows = (len(tiles) + cols - 1) // cols
        sh = Image.new('RGB', (tw * cols, th * rows), (40, 40, 40))
        for k, t in enumerate(tiles): sh.paste(t, ((k % cols) * tw, (k // cols) * th))
        sh.save(os.path.join(o.out, 'events_sheet.png'))
    print(f'{len(events)} activity windows in {dur:.1f} s ({W}×{Hh}) → {o.out}/events.json, events_sheet.png ← Read it, then write a plan')
    for e in events:
        first = next((l['text'] for l in reversed(e.get('lines', [])) if l['text'].strip()), '')
        print(f"  #{e['i']:02d} {e['t0']:6.2f}–{e['t1']:6.2f}s  settled {e['settle']:6.2f}s  {e['kind']:<13} last line: {first[:60]}")

def find(o):
    J = json.load(open(os.path.join(o.out, 'events.json'))); evs = [e for e in J['events'] if e.get('lines')]
    if not evs: sys.exit('no OCR lines in events.json (run scan on macOS without --no-ocr)')
    if o.at is not None: evs = [min(evs, key=lambda e: abs(e['settle'] - o.at))]
    hit = 0
    for e in evs:
        L = e['lines']
        for l in L:
            if o.text.lower() not in l['text'].lower(): continue
            x, y, w, h = l['box']; parts = [l]
            if o.row or o.below:   # Vision splits column-aligned terminal output into pieces: take the whole visual row
                cy = y + h / 2; parts = [q for q in L if abs(q['box'][1] + q['box'][3] / 2 - cy) < h * 0.6]
            if o.below:            # + the next N rows (wrapped continuation lines)
                rows = sorted({round(q['box'][1] + q['box'][3] / 2) for q in L if q['box'][1] > y + h * 0.6})
                for r_ in rows[:o.below]: parts += [q for q in L if abs(q['box'][1] + q['box'][3] / 2 - r_) < h * 0.6]
            x0 = min(q['box'][0] for q in parts); y0 = min(q['box'][1] for q in parts)
            x1 = max(q['box'][0] + q['box'][2] for q in parts); y1 = max(q['box'][1] + q['box'][3] for q in parts); p = o.pad
            txt = ' '.join(q['text'] for q in sorted(parts, key=lambda q: (q['box'][1] // max(1, h), q['box'][0])))
            print(json.dumps({'settle': e['settle'], 'text': txt[:100], 'box': [max(0, x0 - p), max(0, y0 - p), x1 - x0 + 2 * p, y1 - y0 + 2 * p]}, ensure_ascii=False)); hit += 1
    if not hit: sys.exit(f'"{o.text}" not found' + (f' near {o.at} s' if o.at is not None else ''))

def build_map(plan, start):
    """plan items → (map [[projT, footT]…], badges [[a,b,speed]…]); 1 ms cuts between items"""
    m, badges, t = [], [], start
    for k, it in enumerate(plan):
        if 'play' in it:
            a, b = it['play']; d = it['dur'] if 'dur' in it else (b - a) / it.get('speed', 1)
            if d <= 0: sys.exit(f'plan item {k}: empty play')
            sp = (b - a) / d; m += [[round(t + (0.001 if m else 0), 3), a], [round(t + d, 3), b]]
            if sp >= 1.5: badges.append([round(t, 3), round(t + d, 3), round(sp)])
        elif 'hold' in it:
            f = it['hold']; d = it['dur']; m += [[round(t + (0.001 if m else 0), 3), f], [round(t + d, 3), f]]
        else: sys.exit(f'plan item {k}: need "play" or "hold"')
        t += d
    return m, badges, round(t, 3)

def mapcmd(o):
    plan = json.load(open(o.plan)); m, badges, end = build_map(plan, o.start)
    print(json.dumps({'map': m, 'badges': badges}, separators=(',', ':')))
    print(f'// project {o.start:g}–{end:g} s ({end - o.start:.2f} s) from {len(plan)} plan items', file=sys.stderr)

def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); s = a.add_subparsers(dest='cmd', required=True)
    p = s.add_parser('scan'); p.add_argument('src'); p.add_argument('out'); p.add_argument('--fps', type=float, default=10)
    p.add_argument('--thr', type=float, default=0.05); p.add_argument('--no-ocr', action='store_true')
    p = s.add_parser('find'); p.add_argument('out'); p.add_argument('text'); p.add_argument('--at', type=float); p.add_argument('--pad', type=int, default=6)
    p.add_argument('--row', action='store_true', help='the whole visual row'); p.add_argument('--below', type=int, default=0, help='+ N following rows (wraps)')
    p = s.add_parser('map'); p.add_argument('plan'); p.add_argument('--start', type=float, default=0.0)
    o = a.parse_args(); {'scan': scan, 'find': find, 'map': mapcmd}[o.cmd](o)

if __name__ == '__main__':
    main()
