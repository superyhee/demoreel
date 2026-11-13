#!/usr/bin/env python3
"""Visual review — the taste layer the numeric QA can't measure. Picks the frames a reviewer would look at (hook, every
camera hold and the middle of every move, callouts, headline cards, end card), and either
  (default)  writes a labelled contact sheet + rubric for the AGENT to read and score (free, no API key), or
  (--api)    sends the frames + rubric to Claude and writes a scored review (costs API credits — opt in).

usage: visual_review.py site/index.html out_dir [--lang zh] [--aspect 9:16] [--max 16]
                        [--mp4 final.mp4]                 # review the encoded film instead of the live page (same frames)
                        [--same-frames prev_dir]          # re-use the previous round's frame times (compare like with like)
                        [--compare prev_dir]              # previous issues → fixed / persistent / new (+ score deltas)
                        [--api [--provider anthropic|bedrock] [--region us-east-1] [--model claude-opus-5-5]] [--dry-run]
Writes out_dir/frames/*.jpg, frames.json, sheet_*.png (Read these), rubric.md; with --api also review.json + review.md
(+ compare.md with --compare). Iterate: fix → re-run with --same-frames R1 --compare R1 → act on persistent + new issues.
Exit 1 when (--api) any criterion scores 0.
"""
import argparse, base64, json, os, subprocess, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_util import open_page, cam_segments, ASPECTS

RUBRIC = [   # (key, criterion) — scored 0 = fails / 1 = acceptable / 2 = commercial quality, with frame evidence
    ('hook', 'First 3 s: a pain or a surprising result, readable at a glance — never logo-only or an empty UI.'),
    ('focus', 'Every frame has ONE obvious place to look (camera, spotlight or callout lead the eye).'),
    ('legibility', 'Key text is readable on a phone (UI text, captions, callouts); nothing important is tiny or low-contrast.'),
    ('framing', 'No awkward crops of the element being explained, no accidental empty canvas, margins look intentional for this aspect ratio.'),
    ('collisions', 'No overlays colliding: headline over the target, callout over text, subtitles over UI being shown, cursor hiding the click target.'),
    ('polish', 'Alignment, spacing, shadows and corner radii look designed; no glitches, half-drawn states, placeholder text or lorem ipsum.'),
    ('story', 'The frames read as ONE task from start to finish and each beat ends in a visible result.'),
    ('restraint', 'No clutter: at most ~3 overlay layers, headline cards short, decoration does not compete with the product.'),
    ('end_card', 'End card: product name + exactly one clear call to action, nothing else competing.'),
    ('trust', 'Data looks plausible and fictional; no real personal data, emails, paths or tokens visible anywhere.'),
]
SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['scores', 'issues', 'previous', 'top_fixes', 'overall'],
    'properties': {
        'scores': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                   'required': ['key', 'score', 'frames', 'evidence', 'fix'],
                   'properties': {'key': {'type': 'string', 'enum': [k for k, _ in RUBRIC]},
                                  'score': {'type': 'integer', 'enum': [0, 1, 2]},
                                  'frames': {'type': 'array', 'items': {'type': 'string'}},
                                  'evidence': {'type': 'string'}, 'fix': {'type': 'string'}}}},
        'issues': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'required': ['title', 'key', 'frames', 'prev'],
                   'properties': {'title': {'type': 'string'}, 'key': {'type': 'string', 'enum': [k for k, _ in RUBRIC]},
                                  'frames': {'type': 'array', 'items': {'type': 'string'}},
                                  'prev': {'type': 'integer'}}}},   # 1-based number of the matching previous issue, 0 = new
        'previous': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'required': ['n', 'status', 'evidence'],
                     'properties': {'n': {'type': 'integer'}, 'status': {'type': 'string', 'enum': ['fixed', 'persistent', 'unclear']},
                                    'evidence': {'type': 'string'}}}},
        'top_fixes': {'type': 'array', 'items': {'type': 'string'}},
        'overall': {'type': 'string'}}}

def pick_times(pg, n_max):
    C = pg.evaluate('''(()=>{const C=window.DEMO_CFG||{};return {d:C.duration||window.DURATION||30,ci:C.camIn||null,co:C.camOut||null,
        notes:(C.notes||[]).map(n=>[n.t0,n.t1,n.label||'']),caps:(C._caps||C.captions||[]).map(c=>[c[0],c[1]])}})()''')
    D = C['d']; ts = []
    ts += [(0.8, 'hook'), (1.6, 'hook'), (2.5, 'hook')]
    segs = cam_segments(pg); ci = C['ci'][1] if C['ci'] else 0
    first = next(((a, b) for a, b, hold in segs if hold and b > ci), None)   # the establishing shot, once it has settled
    for a, b, hold in segs:   # holds: their settled end state (what the engine frames, see measureT); moves: mid-move
        ts.append((max(a, ci, b - 0.4), 'establish' if (a, b) == first else 'hold') if hold else ((a + b) / 2, 'move'))
    ts += [(min(a + 0.8, (a + b) / 2), f'callout "{lab[:30]}"') for a, b, lab in C['notes']]
    ts += [(a + 0.6, 'headline') for a, b in C['caps']]
    ts.append((D - 0.8, 'end card'))
    out = []
    for t, why in sorted((max(0, min(D - 0.05, t)), w) for t, w in ts):
        if out and t - out[-1][0] < 0.35: out[-1] = (out[-1][0], out[-1][1] + ' + ' + why); continue
        out.append((t, why))
    if len(out) > n_max:   # keep hook + end, thin the middle evenly
        mid = out[1:-1]; k = n_max - 2; out = [out[0]] + [mid[round(i * (len(mid) - 1) / max(1, k - 1))] for i in range(k)] + [out[-1]]
    return out, D

def load_prev(d):
    """previous round: frame times (frames.json, or parsed from rubric.md of older runs), review.json, its issue list"""
    if not d: return None
    P = {'dir': d, 'frames': None, 'review': None, 'issues': []}
    fj, rm, rj = (os.path.join(d, x) for x in ('frames.json', 'rubric.md', 'review.json'))
    if os.path.exists(fj): P['frames'] = [(f['t'], f['why']) for f in json.load(open(fj))]
    elif os.path.exists(rm):
        import re
        P['frames'] = [(float(m.group(1)), m.group(2)) for m in re.finditer(r'^- #\d+ ([\d.]+)s — (.*?) — `', open(rm).read(), re.M)]
    if os.path.exists(rj):
        R = P['review'] = json.load(open(rj))
        P['issues'] = [i['title'] for i in R.get('issues', [])] or \
                      [f"{s['key']}: {s['evidence'][:160]}" for s in R['scores'] if isinstance(s['score'], int) and s['score'] < 2]   # older runs: the problem, not the fix
    return P

def grab(o, frames_dir, times=None):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b, pg, _, errs = open_page(p, o.page, o.lang, aspect=o.aspect)
        if errs: sys.exit('page error: ' + errs[0])
        ts, D = pick_times(pg, o.max)
        if times: ts = [(t, why) for t, why in times if t < D]   # same frames as the previous round
        files = []
        for i, (t, why) in enumerate(ts):
            f = os.path.join(frames_dir, f'{i:02d}_{t:05.2f}s.jpg')
            if o.mp4:
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', o.mp4, '-frames:v', '1', '-q:v', '3', f], check=True)
            else:
                pg.evaluate(f'render({t})'); pg.wait_for_timeout(40); png = f + '.png'; pg.screenshot(path=png)
                Image.open(png).convert('RGB').save(f, quality=88); os.remove(png)
            files.append((f, t, why))
        b.close()
    return files, D

def sheets(files, out_dir, per=6, cols=3, tw=800):
    paths = []
    for s in range(0, len(files), per):
        ims = []
        for f, t, why in files[s:s + per]:
            im = Image.open(f); im = im.resize((tw, round(tw * im.height / im.width))); d = ImageDraw.Draw(im)
            lab = f'#{files.index((f, t, why)):02d}  {t:.2f}s  {why}'[:70]; d.rectangle((0, 0, 8 + 7 * len(lab), 24), fill=(0, 0, 0)); d.text((6, 6), lab, fill=(255, 255, 255))
            ims.append(im)
        th = ims[0].height; rows = (len(ims) + cols - 1) // cols; sh = Image.new('RGB', (tw * cols, th * rows), (255, 255, 255))
        for i, im in enumerate(ims): sh.paste(im, ((i % cols) * tw, (i // cols) * th))
        p = os.path.join(out_dir, f'sheet_{len(paths) + 1}.png'); sh.save(p); paths.append(p)
    return paths

def rubric_md(files, D, o):
    L = [f'# Visual review — {os.path.basename(o.page)} ({o.aspect or "page default"} · {o.lang} · {D:g} s)', '',
         'Frames (open the sheets; each tile is labelled `#NN  time  why`):', '']
    L += [f'- #{i:02d} {t:.2f}s — {why} — `{os.path.relpath(f, o.out)}`' for i, (f, t, why) in enumerate(files)]
    L += ['', 'Score each criterion 0 (fails) / 1 (acceptable) / 2 (commercial quality). Cite frames (#NN), say what you see,',
          'give ONE concrete fix (selector, time, config key). Be strict: a 2 means you would ship it in a launch film.', '',
          '| key | criterion | score | frames | evidence | fix |', '|---|---|---|---|---|---|']
    L += [f'| {k} | {c} |  |  |  |  |' for k, c in RUBRIC]
    if o.prev and o.prev['issues']:
        L += ['', f'Previous round ({o.prev["dir"]}) — mark each issue fixed / persistent / unclear, citing the same frames:', '',
              '| # | previous issue | status | evidence |', '|---|---|---|---|']
        L += [f'| {n} | {t} |  |  |' for n, t in enumerate(o.prev['issues'], 1)]
        L += ['', 'Then list NEW issues separately (not seen last round).']
    L += ['', 'Then list the top 3 fixes in priority order, apply them, re-run with --same-frames/--compare and compare.']
    return '\n'.join(L) + '\n'

SYSTEM = ('You are a senior motion designer reviewing a software product demo film before release. You see still frames sampled at '
          'the moments that matter (hook, camera holds, the middle of camera moves, callouts, headline cards, end card). Judge what is '
          'visible only; do not invent motion you cannot see. Be specific and strict — cite frame ids, name the element, give one '
          'concrete fix each. Reply in the language of the film\'s captions when they are not English.')

def api_review(files, D, o):
    content = []
    for i, (f, t, why) in enumerate(files):
        content.append({'type': 'text', 'text': f'Frame #{i:02d} at {t:.2f}s ({why}):'})
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': base64.standard_b64encode(open(f, 'rb').read()).decode()}})
    content.append({'type': 'text', 'text': f'Film: {D:g} s, aspect {o.aspect or "16:9"}, language {o.lang}. Score every criterion '
                    '(0 fails / 1 acceptable / 2 commercial quality) with frame ids, evidence and one fix; then the top 3 fixes.\n' +
                    '\n'.join(f'- {k}: {c}' for k, c in RUBRIC) +
                    '\nAlso list every visible problem in `issues` (short title, criterion key, frame ids).' +
                    (('\n\nPrevious review of the SAME frames found these issues. In `previous`, mark each one fixed / persistent / '
                      'unclear by what is visible NOW, with evidence. In `issues`, set prev = the matching previous number, 0 if new.\n' +
                      '\n'.join(f'{n}. {t}' for n, t in enumerate(o.prev['issues'], 1)))
                     if o.prev and o.prev['issues'] else '\nThere is no previous review: return previous = [] and prev = 0.')})
    req = dict(model=o.model, max_tokens=16000, system=SYSTEM, messages=[{'role': 'user', 'content': content}])
    # output_config / fallbacks via extra_body: works on older installed SDKs that predate these parameters
    extra = {'output_config': {'effort': 'high', 'format': {'type': 'json_schema', 'schema': SCHEMA}}}
    if o.dry_run:
        size = sum(len(c.get('source', {}).get('data', '')) for c in content)
        print(f'dry run: {len(files)} frames, {size / 1e6:.1f} MB base64, model {o.model} via {o.provider} — nothing sent'); return None
    import anthropic
    if o.provider == 'bedrock':
        if not hasattr(anthropic, 'AnthropicBedrockMantle'): sys.exit('bedrock: upgrade the SDK (pip install -U anthropic) for AnthropicBedrockMantle')
        client = anthropic.AnthropicBedrockMantle(aws_region=o.region); req['model'] = 'anthropic.' + o.model
        stream = client.messages.stream(**req, extra_body=extra)          # server-side fallbacks are not available on Bedrock
    else:
        client = anthropic.Anthropic()
        extra['fallbacks'] = 'default'                                     # a classifier decline re-runs on the recommended fallback model
        stream = client.beta.messages.stream(**req, betas=['server-side-fallback-2026-07-01'], extra_body=extra)
    try:
        with stream as st: resp = st.get_final_message()                   # streamed: long reviews don't hit the request timeout
    except anthropic.NotFoundError as e:
        sys.exit(f'{req["model"]} not found ({e.message[:120]}) — on Bedrock the model may only be served in some regions: try --region us-east-1')
    if resp.stop_reason == 'refusal': sys.exit(f'review declined (stop_reason=refusal): {getattr(resp, "stop_details", None)}')
    if resp.stop_reason == 'max_tokens': sys.exit('review truncated (max_tokens) — rerun with fewer frames (--max)')
    text = next(b.text for b in resp.content if b.type == 'text')
    return json.loads(text)

def compare_md(r, P):
    """score deltas per criterion + previous issues fixed / persistent / unclear + new issues"""
    old = {s['key']: s['score'] for s in P['review']['scores']}; new = {s['key']: s['score'] for s in r['scores']}
    tot = lambda d: sum(v for v in d.values() if isinstance(v, int))
    L = [f'## Compared with {P["dir"]}', '', f'**{tot(old)} → {tot(new)}** / {2 * len(RUBRIC)}', '', '| key | before | now |', '|---|---|---|']
    L += [f'| {k} | {old.get(k, "?")} | {new.get(k, "?")}{" ▲" if new.get(k, 0) > old.get(k, 0) else " ▼" if new.get(k, 0) < old.get(k, 0) else ""} |' for k, _ in RUBRIC]
    st = {p['n']: p for p in r.get('previous', [])}
    for label, want in (('Fixed', 'fixed'), ('Still there', 'persistent'), ('Unclear', 'unclear')):
        rows = [f'- {P["issues"][n - 1]} — {st[n]["evidence"]}' for n in sorted(st) if st[n]['status'] == want and 0 < n <= len(P['issues'])]
        if rows: L += ['', f'**{label}** ({len(rows)})'] + rows
    nu = [i for i in r.get('issues', []) if not i.get('prev')]
    if nu: L += ['', f'**New** ({len(nu)})'] + [f'- [{i["key"]}] {i["title"]} ({" ".join(i["frames"])})' for i in nu]
    return '\n'.join(L) + '\n'

def main():
    a = argparse.ArgumentParser(); a.add_argument('page'); a.add_argument('out'); a.add_argument('--lang', default='zh')
    a.add_argument('--aspect', choices=ASPECTS); a.add_argument('--max', type=int, default=16); a.add_argument('--mp4')
    a.add_argument('--api', action='store_true'); a.add_argument('--provider', choices=['anthropic', 'bedrock'], default='anthropic')
    a.add_argument('--region', default=os.environ.get('AWS_REGION', 'us-east-1')); a.add_argument('--model', default='claude-opus-5-5')
    a.add_argument('--dry-run', action='store_true'); a.add_argument('--same-frames'); a.add_argument('--compare'); o = a.parse_args()
    o.prev = load_prev(o.compare or o.same_frames)
    sf = load_prev(o.same_frames) if o.same_frames else None
    if o.same_frames and not (sf and sf['frames']): sys.exit(f'--same-frames: no frames.json / rubric.md in {o.same_frames}')
    fd = os.path.join(o.out, 'frames'); os.makedirs(fd, exist_ok=True)
    for f in os.listdir(fd): os.remove(os.path.join(fd, f))
    files, D = grab(o, fd, sf['frames'] if sf else None); sh = sheets(files, o.out)
    json.dump([{'i': i, 't': t, 'why': w, 'file': os.path.relpath(f, o.out)} for i, (f, t, w) in enumerate(files)],
              open(os.path.join(o.out, 'frames.json'), 'w'), ensure_ascii=False, indent=1)
    open(os.path.join(o.out, 'rubric.md'), 'w').write(rubric_md(files, D, o))
    print(f'{len(files)} frames → {", ".join(sh)}  ← Read them, score {os.path.join(o.out, "rubric.md")}')
    if not o.api: return
    r = api_review(files, D, o)
    if r is None: return
    json.dump(r, open(os.path.join(o.out, 'review.json'), 'w'), ensure_ascii=False, indent=1)
    by = {s['key']: s for s in r['scores']}; L = ['| key | score | frames | evidence | fix |', '|---|---|---|---|---|']
    for k, _ in RUBRIC:
        s = by.get(k, {'score': '?', 'frames': [], 'evidence': 'not scored', 'fix': ''})
        L.append(f"| {k} | {s['score']} | {' '.join(s['frames'])} | {s['evidence']} | {s['fix']} |")
    tot = sum(s['score'] for s in r['scores'] if isinstance(s['score'], int))
    L += ['', f'**{tot}/{2 * len(RUBRIC)}** — {r["overall"]}', '', 'Top fixes:'] + [f'{i + 1}. {x}' for i, x in enumerate(r['top_fixes'])]
    if o.compare and o.prev and o.prev['review']:
        C = compare_md(r, o.prev); open(os.path.join(o.out, 'compare.md'), 'w').write(C); L += ['', C]
    open(os.path.join(o.out, 'review.md'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))
    sys.exit(1 if any(s['score'] == 0 for s in r['scores']) else 0)

if __name__ == '__main__':
    main()
