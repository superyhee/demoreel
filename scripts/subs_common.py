"""Shared subtitle phrasing + output (used by subtitle_marks.py and align_subs.py).
tokens: [{'t': seconds, 'text': display text incl. trailing space/punctuation}] in order, per VO line."""
import json, os, re

PUNCT = set('，。！？；：、,.!?;:')

def width(s):
    s = re.sub(r'\s', '', s); return sum(1 if ord(ch) > 0x2e80 else 0.55 for ch in s)   # latin ≈ ½ CJK

def phrases(toks, maxw=16, line_end=None):
    """Split one VO line's tokens into on-screen phrases: sentence ends at ≥6 width, commas at ≥45 % of maxw, hard break at maxw."""
    items, cur, n = [], [], 0
    def flush(end):
        nonlocal cur, n
        if cur: items.append({'t0': cur[0]['t'], 't1': round(end, 3), 'words': cur}); cur, n = [], 0
    for i, tk in enumerate(toks):
        vis = width(tk['text'])
        if cur and n + vis > maxw: flush(tk['t'] - 0.05)
        cur.append(tk); n += vis
        e = tk['text'].strip()[-1:] if tk['text'].strip() else ''
        if e and e in PUNCT and n >= (6 if e in '。！？.!?' else max(6, maxw * 0.45)) and i + 1 < len(toks): flush(toks[i + 1]['t'] - 0.05)
    if toks: flush(line_end if line_end else toks[-1]['t'] + 0.25 + 0.12 * len(toks[-1]['text']))
    return items

def write(items, out, keywords=''):
    json.dump(items, open(out, 'w'), ensure_ascii=False, indent=0)
    kw = [k.strip() for k in keywords.split(',') if k.strip()]
    open(os.path.splitext(out)[0] + '.js', 'w').write('window.SUBS=' + json.dumps(items, ensure_ascii=False) + ';window.SUBS_KW=' + json.dumps(kw, ensure_ascii=False) + ';\n')
    ts = lambda t: '%02d:%02d:%02d,%03d' % (int(t // 3600), int(t % 3600 // 60), int(t % 60), int(round(t % 1 * 1000)) % 1000)
    srt = os.path.splitext(out)[0] + '.srt'   # for players / platforms with native captions (YouTube, LinkedIn, WeChat Channels)
    open(srt, 'w').write('\n'.join(f"{i + 1}\n{ts(x['t0'])} --> {ts(x['t1'])}\n{''.join(w['text'] for w in x['words']).strip()}\n" for i, x in enumerate(items)))
    print(f'{len(items)} subtitle phrases → {out} (+ .js, .srt)')
    for x in items[:6]: print(f"  {x['t0']:7.2f}–{x['t1']:7.2f}  {''.join(w['text'] for w in x['words'])}")
