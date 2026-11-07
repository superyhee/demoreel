import sys
#!/usr/bin/env python3
"""Word-timed subtitles from the VO script via Amazon Polly speech marks (same voice/engine as tts_polly.sh).
Splits each line into short phrases (≤ --max chars, at punctuation; keeps the original punctuation) and writes
subs.json: [{"t0":..,"t1":..,"words":[{"t":..,"text":".."},..]}, ..]  → Demo.init({subtitles:{items: <subs.json>}})
usage: subtitle_marks.py vo.tsv subs.json [--voice Zhiyu] [--engine neural] [--lang cmn-CN] [--max 16]"""
import argparse, json, subprocess, tempfile, os, re
a=argparse.ArgumentParser(); a.add_argument('tsv'); a.add_argument('out'); a.add_argument('--voice',default='Zhiyu'); a.add_argument('--engine',default='neural')
a.add_argument('--lang',default='cmn-CN'); a.add_argument('--keywords',default='',help='comma-separated words to accent'); a.add_argument('--max',type=int,default=16); a.add_argument('--region',default='us-east-1'); o=a.parse_args()
PUNCT=set('，。！？；：、,.!?;:')
items=[]
for line in open(o.tsv,encoding='utf-8'):
    if not line.strip(): continue
    st,text=line.rstrip('\n').split('\t',1); st=float(st); f=tempfile.mktemp(suffix='.json')
    cmd=['aws','polly','synthesize-speech','--region',o.region,'--engine',o.engine,'--voice-id',o.voice,'--output-format','json','--speech-mark-types','["word"]','--text',text,f]
    if o.lang: cmd[-1:-1]=['--language-code',o.lang]   # before the outfile
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode and o.engine!='neural':   # generative voices don't return speech marks → time with the neural voice (render the VO with neural too for exact sync)
        print(f'note: {o.engine} engine gave no speech marks ({r.stderr.strip()[:80]}) → using neural timings',file=sys.stderr); o.engine='neural'
        cmd[cmd.index('--engine')+1]='neural'; r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: sys.exit('polly failed: '+r.stderr.strip())
    marks=[json.loads(l) for l in open(f) if l.strip()]; os.remove(f); b=text.encode('utf-8')
    # display tokens = text between consecutive word starts (keeps spaces/punctuation attached to the preceding word)
    toks=[]
    for i,m in enumerate(marks):
        s0=m['start']; s1=marks[i+1]['start'] if i+1<len(marks) else len(b)
        toks.append({'t':round(st+m['time']/1000,3),'text':b[s0:s1].decode('utf-8','ignore')})
    if marks and marks[0]['start']>0: toks[0]['text']=b[:marks[0]['start']].decode('utf-8','ignore')+toks[0]['text']
    # phrase split: break after punctuation once the phrase is long enough, or hard-break at --max visible chars
    cur=[];n=0
    def flush(end):
        global cur,n
        if cur: items.append({'t0':cur[0]['t'],'t1':end,'words':cur}); cur=[];n=0
    for i,tk in enumerate(toks):
        t_=re.sub(r'\s','',tk['text']); vis=sum(1 if ord(ch)>0x2e80 else 0.55 for ch in t_)   # display width: latin ≈ ½ CJK
        if cur and n+vis>o.max: flush(tk['t']-0.05)
        cur.append(tk); n+=vis
        e=tk['text'].strip()[-1:] if tk['text'].strip() else ''
        # sentence ends split at ≥6 width; commas only once the phrase is ≥45 % of --max (keeps "Priorities, sorted." together)
        if e and e in PUNCT and n>=(6 if e in '。！？.!?' else max(6,o.max*0.45)) and i+1<len(toks): flush(toks[i+1]['t']-0.05)
    last=toks[-1]['t'] if toks else st
    flush(round(last+0.25+0.12*len(toks[-1]['text']),3) if toks else st+1)
for k in range(len(items)-1): items[k]['t1']=min(items[k]['t1'],items[k+1]['t0']-0.04)
json.dump(items,open(o.out,'w'),ensure_ascii=False,indent=0)
# also write <out>.js next to it: pages load it with <script src="subs.js"></script> and the engine picks window.SUBS up automatically
import os
kw=[k.strip() for k in o.keywords.split(',') if k.strip()]
open(os.path.splitext(o.out)[0]+'.js','w').write('window.SUBS='+json.dumps(items,ensure_ascii=False)+';window.SUBS_KW='+json.dumps(kw,ensure_ascii=False)+';\n')
print(f'{len(items)} subtitle phrases → {o.out}'); [print(f"  {x['t0']:7.2f}–{x['t1']:7.2f}  {''.join(w['text'] for w in x['words'])}") for x in items[:6]]
