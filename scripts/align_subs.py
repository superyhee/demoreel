#!/usr/bin/env python3
"""Word-timed subtitles for ANY TTS (or a human VO recording) by local forced alignment with faster-whisper.

usage: align_subs.py vo.manifest.json site/subs.json [--lang zh] [--model small] [--max 16] [--keywords "Kiro,一键"]
       align_subs.py --tsv vo.tsv --audio vo.wav site/subs.json ...      # one mixed VO file + the script (human VO)
The DISPLAYED text is always your script (vo.tsv), never the recognizer's guess: whisper only supplies timing. Its words are
spread over characters and matched to the script with difflib; unmatched characters are interpolated, so recognition errors
(数字/同音字/English terms) never reach the screen. Output = same subs.json/subs.js format as subtitle_marks.py.
Needs: pip install faster-whisper (first run downloads the model from Hugging Face; 'small' ≈ 480 MB, 'base' ≈ 145 MB).
"""
import argparse, json, os, re, sys, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subs_common import phrases, write

def norm(ch): return ch.lower() if ch.isalnum() else ''

def tokens_of(text):
    """display tokens: CJK = one char each, latin = a word; trailing spaces/punctuation stay attached."""
    toks = re.findall(r'[⺀-鿿豈-﫿]|[A-Za-z0-9][A-Za-z0-9._%@+#&\'’-]*|[^\sA-Za-z0-9⺀-鿿]', text)
    out, pos = [], 0
    for t in toks:
        i = text.index(t, pos)
        if out and i > pos: out[-1]['text'] += text[pos:i]          # whitespace between tokens
        if out and not re.match(r'[⺀-鿿A-Za-z0-9]', t): out[-1]['text'] += t; pos = i + len(t); continue   # punctuation
        out.append({'text': t, 'c0': i}); pos = i + len(t)
    if out: out[-1]['text'] += text[pos:]
    return out

def align_line(model, audio, text, lang, offset=0.0, clip=None, lead=0.11):
    kw = dict(language=lang, word_timestamps=True, vad_filter=False, beam_size=5, initial_prompt=text)
    if clip: kw['clip_timestamps'] = clip
    segs, _ = model.transcribe(audio, **kw)
    rc, rt = [], []                                      # recognized chars + times
    for s in segs:
        for w in s.words or []:
            cs = [c for c in w.word if norm(c)]
            for k, c in enumerate(cs): rc.append(norm(c)); rt.append(w.start + (w.end - w.start) * (k + 0.5) / len(cs))
    src = [(i, norm(c)) for i, c in enumerate(text) if norm(c)]
    T = [None] * len(text)
    if rc:
        sm = difflib.SequenceMatcher(None, [c for _, c in src], rc, autojunk=False)
        for a_, b_, n in sm.get_matching_blocks():
            for k in range(n): T[src[a_ + k][0]] = rt[b_ + k]
    known = [(i, t) for i, t in enumerate(T) if t is not None]
    if not known:                                        # nothing recognized → proportional fallback over the clip
        d = rt[-1] if rt else 1.0; known = [(0, 0.0), (len(text) - 1, d)]
    for i in range(len(text)):                          # interpolate the gaps
        if T[i] is None:
            prev = max((k for k in known if k[0] < i), default=None, key=lambda k: k[0]); nxt = min((k for k in known if k[0] > i), default=None, key=lambda k: k[0])
            if prev and nxt: T[i] = prev[1] + (nxt[1] - prev[1]) * (i - prev[0]) / (nxt[0] - prev[0])
            else: T[i] = (prev or nxt)[1]
    toks = tokens_of(text)
    for t in toks: t['t'] = round(max(offset, offset + T[t.pop('c0')] - lead), 3)   # whisper word starts lag ≈ 80 ms → lead
    for k in range(1, len(toks)): toks[k]['t'] = max(toks[k]['t'], toks[k - 1]['t'] + 0.02)   # monotonic
    return toks

def main():
    a = argparse.ArgumentParser(); a.add_argument('inputs', nargs='+'); a.add_argument('--lang', default='zh'); a.add_argument('--model', default='small')
    a.add_argument('--max', type=int, default=None); a.add_argument('--keywords', default=''); a.add_argument('--tsv'); a.add_argument('--audio'); a.add_argument('--lead', type=float, default=0.11, help='seconds to shift highlights earlier (measured whisper lag ≈ 0.08 s + 0.03 s anticipation)')
    o = a.parse_args(); out = o.inputs[-1]
    lang = {'cmn-CN': 'zh', 'zh-CN': 'zh', 'en-US': 'en', 'en-GB': 'en'}.get(o.lang, o.lang.split('-')[0])
    maxw = o.max or (16 if lang in ('zh', 'ja', 'ko') else 30)
    try: from faster_whisper import WhisperModel
    except ImportError: sys.exit('ERROR: pip install faster-whisper (see docs/voiceover.md)')
    model = WhisperModel(o.model, device='auto', compute_type='int8')
    items = []
    if o.tsv and o.audio:                                 # one mixed file: align each line inside [start, next start)
        lines = [l.rstrip('\n').split('\t', 1) for l in open(o.tsv, encoding='utf-8') if '\t' in l and l.strip()]
        for k, (st, text) in enumerate(lines):
            st = float(st); en = float(lines[k + 1][0]) if k + 1 < len(lines) else st + 30
            toks = align_line(model, o.audio, text, lang, 0.0, [st, en], o.lead); items += phrases(toks, maxw)
    else:
        man = json.load(open(o.inputs[0]))
        for m in man:
            toks = align_line(model, m['clip'], m['text'], lang, m['start'], lead=o.lead); items += phrases(toks, maxw, line_end=m['start'] + m['dur'] + 0.05)
    write(items, out, o.keywords)

if __name__ == '__main__':
    main()
