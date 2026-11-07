#!/usr/bin/env python3
"""Procedural 'tech product demo' score, arranged to the video's cue points (no samples, no licenses needed).
Modern corporate / uplifting electronic: supersaw pads with filter sweeps, sub bass, pluck arp with ping-pong delay,
FM bell lead, layered kick/clap/hats with sidechain pump, risers, impacts, convolution reverb, master glue + limiter.

usage: music_pro.py <out.wav> [--dur 30] [--bpm 120] [--hit 3.55] [--groove 5.0] [--main 9.0]
                    [--lift 21.0] [--peak 23.0] [--drop 26.0] [--end 26.6] [--stems DIR] [--seed 3]
  hit   : logo impact            groove: light beat + arp enter (UI appears)
  main  : full groove            lift  : riser/snare roll build   peak: full + lead
  drop  : drums cut, reverse swell                                 end : final chord hit + tail
Tip: put cue points on the beat grid starting at --groove (multiples of 60/bpm) except hit/end, which can be anywhere."""
import argparse, os, wave
import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi, fftconvolve, sawtooth

ap=argparse.ArgumentParser()
ap.add_argument('out'); ap.add_argument('--dur',type=float,default=30); ap.add_argument('--bpm',type=float,default=120)
for k,v in dict(hit=3.55,groove=5.0,main=9.0,lift=21.0,peak=23.0,drop=26.0,end=26.6).items(): ap.add_argument('--'+k,type=float,default=v)
ap.add_argument('--stems'); ap.add_argument('--seed',type=int,default=3)
A=ap.parse_args()
SR=44100; N=int(SR*(A.dur+0.5)); T=np.arange(N)/SR; rng=np.random.default_rng(A.seed)
BEAT=60/A.bpm; BAR=4*BEAT
def z(): return np.zeros((N,2))
def mono2(x,pan=0.0):
    l=np.cos((pan+1)*np.pi/4); r=np.sin((pan+1)*np.pi/4); return np.stack([x*l*1.414,x*r*1.414],1)
def add(buf,t0,sig):
    i=int(t0*SR)
    if i>=N: return
    if i<0: sig=sig[-i:]; i=0
    j=min(N,i+len(sig)); buf[i:j]+=sig[:j-i]
def hz(m): return 440*2**((m-69)/12)
def lp(x,fc,order=2): return sosfilt(butter(order,min(fc,SR*0.45),'low',fs=SR,output='sos'),x,axis=0)
def hp(x,fc,order=2): return sosfilt(butter(order,fc,'high',fs=SR,output='sos'),x,axis=0)
def bp(x,lo,hi,order=2): return sosfilt(butter(order,[lo,hi],'band',fs=SR,output='sos'),x,axis=0)
def sweep_lp(x,fc_fn,block=1024):
    """time-varying low-pass; fc_fn(t)->Hz"""
    y=np.zeros_like(x); zi=None
    for s in range(0,len(x),block):
        fc=float(np.clip(fc_fn(s/SR),40,SR*0.45)); sos=butter(2,fc,'low',fs=SR,output='sos')
        if zi is None: zi=np.zeros((sos.shape[0],2)+x.shape[1:])
        y[s:s+block],zi=sosfilt(sos,x[s:s+block],axis=0,zi=zi)
    return y
def adsr(n,a,d,s,r,hold):
    t=np.arange(n)/SR; e=np.where(t<a,t/a,np.where(t<a+d,1-(1-s)*(t-a)/d,s))
    rel=np.clip((t-hold)/r,0,1); return e*(1-rel)
def reverb(x,secs=2.6,decay=0.55,pre=0.02,tone=6500):
    n=int(SR*secs); t=np.arange(n)/SR; ir=rng.standard_normal((n,2))*np.exp(-t/decay)[:,None]
    ir=lp(ir,tone); ir[:int(pre*SR)]=0; ir/=np.sqrt((ir**2).sum(0))
    return np.stack([fftconvolve(x[:,c],ir[:,c])[:N] for c in range(2)],1)
def pingpong(x,dt,fb=0.35,n=5,tone=3500):
    y=x.copy(); d=int(dt*SR); src=lp(x,tone)
    for k in range(1,n+1):
        g=fb**k; sh=np.zeros_like(x); sh[d*k:]=src[:-d*k] if d*k<len(x) else 0
        y[:,0]+=g*sh[:,(k+1)%2]*(1 if k%2 else 0.6); y[:,1]+=g*sh[:,k%2]*(0.6 if k%2 else 1)
    return y
sec=lambda a,b:(T>=a)&(T<b)

# ---------- harmony (F major: I - iii - vi - IV), 1 chord per bar
CH=[([53,57,60,64],29),([57,60,64,67],33),([53,57,60,62],26),([53,57,58,62],34)]  # (voicing, bass root)
def chord_at(t): return CH[int(max(0,t)/BAR)%4]

# ---------- PAD: supersaw, filter swept by section
pad=z()
for b in range(int(A.dur/BAR)+2):
    t0=b*BAR; notes,_=CH[b%4]; n=int((BAR+0.6)*SR); tt=np.arange(n)/SR; sig=np.zeros((n,2))
    for m in notes:
        for v,det in enumerate([-0.12,-0.06,0,0.06,0.12]):
            f=hz(m)*2**(det/12*1.0); ph=rng.random()*2*np.pi
            s=sawtooth(2*np.pi*f*tt+ph)*0.2; sig+=mono2(s,(v-2)/2.5)
    sig*=adsr(n,0.35,0.3,0.85,0.6,BAR)[:,None]; add(pad,t0,sig)
def pad_fc(t):
    if t<A.hit: return 350+2000*(t/A.hit)**2
    if t<A.groove: return 2400-900*(t-A.hit)/(A.groove-A.hit)
    if t<A.main: return 1500
    if t<A.drop: return 2600+1200*((t-A.lift)/(A.peak-A.lift) if A.lift<=t<A.peak else (1 if t>=A.peak else 0))
    if t<A.end: return 900
    return 3200*np.exp(-(t-A.end)/2.5)+300
pad=sweep_lp(pad,pad_fc); pad=hp(pad,220); pad-=0.35*bp(pad,260,520)   # clear low-mids for VO
pad_g=np.interp(T,[0,A.hit,A.hit+0.05,A.groove,A.main,A.drop,A.end,A.end+0.05,A.dur],[0.6,1.0,0.5,0.7,0.85,0.9,0.5,1.0,0.0])
pad*=pad_g[:,None]

# ---------- SUB BASS: roots, 8ths with octave bounce in main
bass=np.zeros(N)
def bass_note(t0,m,d,g=1.0):
    n=int(d*SR); tt=np.arange(n)/SR; f=hz(m)
    s=(np.sin(2*np.pi*f*tt)+0.35*np.tanh(3*np.sin(2*np.pi*f*tt)))*adsr(n,0.005,0.08,0.8,0.05,d-0.05); add(bass,t0,s*g)
t=A.groove
while t<A.drop-1e-6:
    _,r=chord_at(t)
    if t<A.main: bass_note(t,r+12,BEAT*2-0.02,0.45); t+=BEAT*2
    else:
        k=int(round((t-A.main)/(BEAT/2)))%8; bass_note(t,r+12+(12 if k in(3,7) else 0),BEAT/2-0.02,1.0 if k%2==0 else 0.75); t+=BEAT/2
bass_note(A.end,29+12,1.2,0.45)
bass=hp(lp(bass,600),38); bass=mono2(bass)

# ---------- PLUCK ARP (additive pluck) + ping-pong delay
arp=z()
def pluck(m,d=0.45):
    n=int(d*SR); tt=np.arange(n)/SR; f=hz(m); s=np.zeros(n)
    for h in range(1,9): s+=np.sin(2*np.pi*f*h*tt)/h*np.exp(-tt*(6+h*5))
    return s*np.minimum(1,tt/0.002)
pat=[0,2,1,3,2,1,3,2]
t=A.groove; k=0
while t<A.drop-1e-6:
    notes,_=chord_at(t); step=BEAT/2 if t<A.main else BEAT/4
    m=sorted(notes)[pat[k%8]%4]+12+(12 if (k%16==15) else 0)
    g=0.7 if t<A.main else (0.85 if t<A.peak else 1.0)
    add(arp,t,mono2(pluck(m)*g,0.35*np.sin(k*0.7))); t+=step; k+=1
arp=pingpong(arp,BEAT*0.75,0.38,5); arp=hp(arp,250)

# ---------- FM BELL LEAD (peak + end)
lead=z()
def bell(m,d=1.2,g=1.0):
    n=int(d*SR); tt=np.arange(n)/SR; f=hz(m); I=2.2*np.exp(-tt*4)
    s=np.sin(2*np.pi*f*tt+I*np.sin(2*np.pi*f*3.5*tt))*np.exp(-tt*2.8)*np.minimum(1,tt/0.003); return s*g
motif=[(0,72),(1.5,69),(2.5,74),(3,72)]   # beat offsets within bar (F major)
b=int(np.ceil(A.main/BAR))
while b*BAR<A.drop-0.3:
    bt=b*BAR; notes,_=CH[b%4]; top=max(notes)+12
    if bt>=A.peak-1e-6 or (bt>=A.main and b%2==1):
        for off,m in motif:
            mm=min([x+12 for x in notes]+[top],key=lambda x:abs(x-m))+12
            add(lead,bt+off*BEAT,mono2(bell(mm,1.0,0.8 if bt<A.peak else 1.0),0.2))
    b+=1
for i,m in enumerate([77,81,84,89]): add(lead,A.end+i*0.07,mono2(bell(m,2.6,0.9),(i-1.5)/3))

# ---------- DRUMS
kick=np.zeros(N); clap=z(); hats=z(); kicks=[]
def kick_hit(t0,g=1.0):
    n=int(0.45*SR); tt=np.arange(n)/SR; f=45+110*np.exp(-tt*35); ph=2*np.pi*np.cumsum(f)/SR
    s=np.tanh(1.8*np.sin(ph)*np.exp(-tt*7.5)); click=rng.standard_normal(n)*np.exp(-tt*600)*0.25
    add(kick,t0,(s+click)*g); kicks.append(t0)
def clap_hit(t0,g=1.0):
    n=int(0.35*SR); tt=np.arange(n)/SR; s=np.zeros(n); nz=rng.standard_normal(n)
    for o in (0,0.011,0.022): s+=np.where(tt>=o,np.exp(-(tt-o)*180),0)
    s+=np.exp(-tt*22)*0.5; s=bp(nz*s,900,5000)
    add(clap,t0,mono2(s*g))
def hat(t0,g=1.0,open_=False,pan=0.0):
    n=int((0.25 if open_ else 0.05)*SR); tt=np.arange(n)/SR; s=hp(rng.standard_normal(n),7000)*np.exp(-tt*(14 if open_ else 110))
    add(hats,t0,mono2(s*g,pan))
t=A.groove; i=0
while t<A.drop-1e-6:
    beat=int(round((t-A.groove)/BEAT))
    if t<A.main:
        if beat%2==0: kick_hit(t,0.75)
        hat(t+BEAT/2,0.5,False,0.3)
    else:
        kick_hit(t,1.0)
        if beat%2==1: clap_hit(t,1.0 if t>=A.peak else 0.85)
        for s16 in range(4):
            tt_=t+s16*BEAT/4; hat(tt_,(0.9 if s16==2 else 0.45),False,(-0.3 if s16%2 else 0.3))
        if beat%4==3: hat(t+BEAT/2,0.6,True,-0.2)
    t+=BEAT
# snare roll in lift (last 2 beats before peak)
r=A.peak-2*BEAT; k=0
while r<A.peak-1e-6: clap_hit(r,0.15+0.35*(k/16)); r+=BEAT/8; k+=1
kick_hit(A.hit,1.0); kick_hit(A.end,1.0)
# sidechain pump
sc=np.ones(N)
for kt in kicks:
    i0=int(kt*SR); i1=min(N,i0+int(0.35*SR)); tt=np.arange(i1-i0)/SR; sc[i0:i1]=np.minimum(sc[i0:i1],1-0.55*np.exp(-tt/0.11))
for buf in (pad,arp): buf*=sc[:,None]
bass*=(0.35+0.65*sc)[:,None]

# ---------- FX: riser, reverse swell, impacts, ticking intro
fx=z()
def riser(t0,t1,g=1.0):
    n=int((t1-t0)*SR); tt=np.arange(n)/SR; d=t1-t0; nz=rng.standard_normal(n); out=np.zeros(n)
    for s in range(0,n,1024):
        c=300+9000*((s/SR)/d)**2; out[s:s+1024]=bp(nz[s:s+1024],c*0.7,min(c*1.4,20000))
    tone=sawtooth(2*np.pi*np.cumsum(220+660*(tt/d)**2)/SR)*0.15
    e=(tt/d)**2.2; s=(out*0.9+lp(tone,3000))*e; add(fx,t0,np.stack([s,np.roll(s,300)],1)*g)
def reverse_swell(t1,d=1.2,g=1.0):
    n=int(d*SR); tt=np.arange(n)/SR; s=hp(rng.standard_normal(n),3000)*(tt/d)**3; add(fx,t1-d,mono2(s*g))
def impact(t0,g=1.0,chord=(53,57,60,64,69)):
    n=int(3.5*SR); tt=np.arange(n)/SR; f=30+60*np.exp(-tt*6); boom=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-tt*2.6)
    nz=lp(rng.standard_normal(n),2500)*np.exp(-tt*5)*0.5; stab=np.zeros(n)
    for m in chord:
        for det in (-0.08,0,0.08): stab+=sawtooth(2*np.pi*hz(m+12)*2**(det/12)*tt)*0.08
    stab=lp(stab*np.exp(-tt*2.2),4000); s=boom*0.42+nz+stab; add(fx,t0,mono2(s*g))
for i in range(int(A.hit/(BEAT/2))):   # clock-like tension ticks during the hook
    tt0=0.1+i*BEAT/2
    if tt0<A.hit-0.3:
        n=int(0.04*SR); x=np.arange(n)/SR; s=np.sin(2*np.pi*(1800 if i%2 else 1200)*x)*np.exp(-x*160)
        add(fx,tt0,mono2(s*(0.25+0.35*tt0/A.hit),(0.4 if i%2 else -0.4)))
riser(max(0,A.hit-1.9),A.hit,0.9); reverse_swell(A.hit,1.0,0.6); impact(A.hit,1.0)
riser(A.lift,A.peak,0.32); reverse_swell(A.peak,0.8,0.3)   # keep low: VO usually runs here
reverse_swell(A.end,A.end-A.drop,0.9); impact(A.end,1.1,(53,57,60,64,67,72))

# ---------- MIX
stems={'pad':pad*0.55,'bass':bass*0.40,'arp':arp*0.45,'lead':lead*0.32,'kick':mono2(kick)*0.52,'clap':clap*0.30,'hats':hats*0.16,'fx':fx*0.55}
wet=reverb(stems['pad']*0.35+stems['arp']*0.45+stems['lead']*0.6+stems['clap']*0.35+stems['fx']*0.4,2.8,0.6)
mixb=sum(stems.values())+wet*0.55
mixb=hp(mixb,28)
# stereo widen (mid/side) above 300Hz
mid=(mixb[:,0]+mixb[:,1])/2; side=(mixb[:,0]-mixb[:,1])/2; side=hp(side,300)*1.25; mixb=np.stack([mid+side,mid-side],1)
# glue compressor (RMS, 2:1 over -14 dBFS) + soft limiter
rms=np.sqrt(np.convolve((mixb**2).mean(1),np.ones(2048)/2048,'same'))+1e-9; lvl=20*np.log10(rms)
gr=np.where(lvl>-12,(-12-lvl)*0.35,0)   # gentle glue, keep the build; mixb*=10**(gr/20)[:,None]
mixb/=np.max(np.abs(mixb))+1e-9; mixb=np.tanh(mixb*1.6)/np.tanh(1.6)
dyn=np.interp(T,[0,A.hit-0.01,A.hit,A.groove,A.main-0.01,A.main,A.lift,A.peak,A.drop,A.drop+0.01,A.end-0.01,A.end,A.dur],[0.8,1.0,1.0,0.78,0.78,0.85,0.85,1.0,1.0,0.7,0.8,1.0,1.0])
fade=np.clip((A.dur-T)/1.2,0,1)*np.minimum(1,T/0.05); mixb*=(dyn*fade)[:,None]; mixb*=0.89/(np.max(np.abs(mixb))+1e-9)
def wav(path,x):
    d=(np.clip(x,-1,1)*32767).astype(np.int16); w=wave.open(path,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes()); w.close()
wav(A.out,mixb[:int(A.dur*SR)])
if A.stems:
    os.makedirs(A.stems,exist_ok=True)
    for k,v in stems.items(): wav(f'{A.stems}/{k}.wav',v/(np.max(np.abs(v))+1e-9)*0.9)
print('music ->',A.out)
