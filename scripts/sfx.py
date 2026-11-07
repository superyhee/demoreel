#!/usr/bin/env python3
"""Synthesize an SFX track from an event list [[t,type,gain],...] (window.SFX dumped by render_frames.py).
usage: sfx.py <sfx.json> <out.wav> [duration] [--lib lib.json]   types: pop click tick whoosh swish suck boom chime shimmer
--lib: real samples from sfx_lib.py (e.g. Kenney CC0), level-matched to the synthesized sound of the same type, rotated per event."""
import numpy as np, wave, json, sys, os, subprocess
LIB=None
if '--lib' in sys.argv: k=sys.argv.index('--lib'); LIB=json.load(open(sys.argv[k+1])); del sys.argv[k:k+2]
sr=44100; DUR=float(sys.argv[3]) if len(sys.argv)>3 else 30; n=int(sr*(DUR+0.5)); out=np.zeros(n); rng=np.random.default_rng(7)
def lp(x,a):  # one-pole lowpass
    y=np.zeros_like(x); s=0.0
    for i,v in enumerate(x): s+=a*(v-s); y[i]=s
    return y
def place(t,sig,g):
    i=int(t*sr); j=min(n,i+len(sig)); out[i:j]+=g*sig[:j-i]
def env(d,a=0.005,dec=8):
    tt=np.arange(int(sr*d))/sr; return tt,np.minimum(1,tt/a)*np.exp(-tt*dec)
def pop():
    tt,e=env(0.12,0.002,40); f=900*np.exp(-tt*18)+300; return e*np.sin(2*np.pi*np.cumsum(f)/sr)*0.5
def click():
    tt,e=env(0.05,0.0005,120); return (np.sin(2*np.pi*2800*tt)*0.5+rng.standard_normal(len(tt))*0.3)*e
def tick():   # soft key 'thock'
    tt,e=env(0.03,0.0005,200); return (np.sin(2*np.pi*1900*tt)*0.25+np.sin(2*np.pi*3800*tt)*0.1+rng.standard_normal(len(tt))*0.15)*e
def noise_sweep(d,rise=True,a0=0.02,a1=0.25):
    m=int(sr*d); x=rng.standard_normal(m); tt=np.arange(m)/sr
    shape=np.sin(np.pi*tt/d)**2 if not rise else (tt/d)**2*np.exp(-np.maximum(0,tt-d*0.85)*40)
    # time-varying lowpass approximation: blend two filtered versions
    lo=lp(x,a0); hi=lp(x,a1); k=np.sin(np.pi*tt/d)
    return (lo*(1-k)+hi*k)*shape
def whoosh(): return noise_sweep(0.6,False,0.02,0.18)*0.9   # soft, low-passed air (not a hard swoosh)
def swish(): return noise_sweep(0.25,False,0.05,0.5)*0.7
def suck(): return noise_sweep(0.6,True,0.02,0.3)*1.2
def boom():
    tt,e=env(1.2,0.002,3.5); f=40+80*np.exp(-tt*12); return e*np.sin(2*np.pi*np.cumsum(f)/sr)*0.9
def bell(fs,d=1.6,dec=3):
    tt,e=env(d,0.003,dec); return e*sum(np.sin(2*np.pi*f*tt)*(0.5**i) for i,f in enumerate(fs))*0.35
def chime():
    a=bell([1318.5,1975.5,2637]); b=np.pad(bell([1760,2637],1.4,3),(int(sr*0.09),0)); m=max(len(a),len(b)); return np.pad(a,(0,m-len(a)))+np.pad(b,(0,m-len(b)))
def shimmer():
    s=np.zeros(int(sr*2.2))
    for k,f in enumerate([1046.5,1318.5,1568,2093]):
        b=bell([f,f*2],1.6,2.5)*0.6; i=int(sr*0.06*k); s[i:i+len(b)]+=b[:len(s)-i]
    return s
G={'pop':pop,'click':click,'tick':tick,'whoosh':whoosh,'swish':swish,'suck':suck,'boom':boom,'chime':chime,'shimmer':shimmer}
cache={}
SAMP={}
if LIB:
    def _load(p):
        raw=subprocess.run(['ffmpeg','-v','error','-i',p,'-f','f32le','-ac','1','-ar',str(sr),'-'],capture_output=True).stdout
        x=np.frombuffer(raw,np.float32).astype(float);nz=np.nonzero(np.abs(x)>1e-3)[0];return x[nz[0]:nz[-1]+1] if len(nz) else x
    for ty,v in LIB['types'].items():
        if v.get('pick') and ty in G:
            ref=np.abs(G[ty]()).max()            # level-match: same peak as the synthesized default → calibrated gains keep their meaning
            SAMP[ty]=[(x/(np.abs(x).max()+1e-9))*ref for x in map(_load,v['pick'])]
    print('library sfx:',{k:len(v) for k,v in SAMP.items()},'synthesized:',[k for k in G if k not in SAMP])
cnt={}
for t,ty,g in json.load(open(sys.argv[1])):
    if ty in SAMP: i=cnt.get(ty,0); cnt[ty]=i+1; sig=SAMP[ty][i%len(SAMP[ty])]          # rotate → no machine-gun repeats
    else: sig=G[ty]() if ty in('tick','click','whoosh','swish') else cache.setdefault(ty,G[ty]())
    place(t,sig,g)
# --- polish: stereo placement, soft top end, short room reverb
from scipy.signal import fftconvolve, butter, sosfilt
L=out.copy(); R=out.copy()
pan=np.zeros(n)   # whooshes/swishes sweep left->right across their length
for t,ty,g in json.load(open(sys.argv[1])):
    if ty in('whoosh','swish'):
        i=int(t*sr); m=int((0.55 if ty=='whoosh' else 0.25)*sr); j=min(n,i+m); pan[i:j]=np.linspace(-0.7,0.7,j-i)
L*=np.cos((pan+1)*np.pi/4)*1.414; R*=np.sin((pan+1)*np.pi/4)*1.414
sos=butter(2,9000,'low',fs=sr,output='sos'); L=sosfilt(sos,L); R=sosfilt(sos,R)
m=int(0.8*sr); tt=np.arange(m)/sr; ir=rng.standard_normal((m,2))*np.exp(-tt/0.18)[:,None]; ir[:int(0.012*sr)]=0; ir/=np.sqrt((ir**2).sum(0))
L=L+0.22*fftconvolve(L,ir[:,0])[:n]; R=R+0.22*fftconvolve(R,ir[:,1])[:n]
st=np.stack([L,R],1)
# FIXED absolute gain (no per-track peak normalisation: removing events must never make the remaining ones louder)
G=float(os.environ.get('SFX_FIXED_GAIN','0.65')); st=np.tanh(st*G*1.2)/1.2
d=(st*32767).astype(np.int16)
w=wave.open(sys.argv[2],'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(d.tobytes()); w.close(); print('ok',sys.argv[2])
