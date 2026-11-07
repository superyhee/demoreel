#!/usr/bin/env python3
"""Multi-style procedural demo scores on the SAME cue points as music_pro.py (interchangeable without re-timing).

styles:
  electronic  uplifting corporate EDM (delegates to music_pro.py)                      default bpm 120
  piano       warm felt piano + string pad, soft 'heartbeat' kick, shaker — trustworthy  bpm 120 (half-time feel)
  lofi        Rhodes jazz chords, swung boom-bap drums, vinyl crackle, tape tone — relaxed bpm 90
  cinematic   staccato string ostinato, taiko, low brass stabs, big impacts — launch / epic bpm 120
  minimal     marimba + glass bell, rim clicks, sub pulse, airy pad — clean 'keynote' tech bpm 120

usage: music_styles.py <out.wav> --style piano [--dur 30] [--bpm N] [--hit 3.55] [--groove 5] [--main 9]
                       [--lift 21] [--peak 23] [--drop 26] [--end 26.6] [--seed 3]
       music_styles.py <out_dir> --all [cue args]      -> <out_dir>/music_<style>.wav for every style
All outputs are mastered to about -11..-13 LUFS like music_pro.py -> mix with MUSIC_GAIN≈0.18."""
import argparse, os, sys, wave, subprocess
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve, sawtooth

STYLES=['electronic','piano','lofi','cinematic','minimal']
BPM={'electronic':120,'piano':120,'lofi':90,'cinematic':120,'minimal':120}
ap=argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--style',default='piano',choices=STYLES); ap.add_argument('--all',action='store_true')
ap.add_argument('--dur',type=float,default=30); ap.add_argument('--bpm',type=float)
CUES=dict(hit=3.55,groove=5.0,main=9.0,lift=21.0,peak=23.0,drop=26.0,end=26.6)
for k,v in CUES.items(): ap.add_argument('--'+k,type=float,default=v)
ap.add_argument('--seed',type=int,default=3)
A=ap.parse_args()
HERE=os.path.dirname(os.path.abspath(__file__))
cue_args=sum([[f'--{k}',str(getattr(A,k))] for k in CUES],[])+['--dur',str(A.dur),'--seed',str(A.seed)]

def normalize(path,target=-12.0,ceil=0.95):
    out=subprocess.run(['ffmpeg','-hide_banner','-i',path,'-af','ebur128=framelog=quiet','-f','null','-'],capture_output=True,text=True).stderr
    I=float([l for l in out.splitlines() if l.strip().startswith('I:')][-1].split()[1])
    w=wave.open(path); p=w.getparams(); x=np.frombuffer(w.readframes(p.nframes),np.int16).astype(float)/32768; w.close()
    g=10**((target-I)/20); g=min(g,ceil/(np.abs(x).max()+1e-9)); x=(np.clip(x*g,-1,1)*32767).astype(np.int16)
    w=wave.open(path,'wb'); w.setparams(p); w.writeframes(x.tobytes()); w.close()
if A.all:
    os.makedirs(A.out,exist_ok=True)
    for s in STYLES:
        out=os.path.join(A.out,f'music_{s}.wav')
        subprocess.run([sys.executable,os.path.abspath(__file__),out,'--style',s]+cue_args,check=True)
    sys.exit(0)
if A.style=='electronic':
    subprocess.run([sys.executable,os.path.join(HERE,'music_pro.py'),A.out,'--bpm',str(A.bpm or 120)]+cue_args,check=True); normalize(A.out); sys.exit(0)

# ======================= shared DSP =======================
SR=44100; N=int(SR*(A.dur+0.5)); T=np.arange(N)/SR; rng=np.random.default_rng(A.seed)
bpm=A.bpm or BPM[A.style]; BEAT=60/bpm; BAR=4*BEAT
def z(): return np.zeros((N,2))
def mono2(x,pan=0.0):
    l=np.cos((pan+1)*np.pi/4); r=np.sin((pan+1)*np.pi/4); return np.stack([x*l*1.414,x*r*1.414],1)
def add(buf,t0,sig):
    i=int(round(t0*SR))
    if i>=N: return
    if i<0: sig=sig[-i:]; i=0
    j=min(N,i+len(sig)); buf[i:j]+=sig[:j-i]
def hz(m): return 440*2**((m-69)/12)
def lp(x,fc,o=2): return sosfilt(butter(o,min(fc,SR*0.45),'low',fs=SR,output='sos'),x,axis=0)
def hp(x,fc,o=2): return sosfilt(butter(o,fc,'high',fs=SR,output='sos'),x,axis=0)
def bp(x,lo,hi,o=2): return sosfilt(butter(o,[lo,min(hi,SR*0.45)],'band',fs=SR,output='sos'),x,axis=0)
def sweep_lp(x,fn,block=1024):
    y=np.zeros_like(x); zi=None
    for s in range(0,len(x),block):
        sos=butter(2,float(np.clip(fn(s/SR),40,SR*0.45)),'low',fs=SR,output='sos')
        if zi is None: zi=np.zeros((sos.shape[0],2)+x.shape[1:])
        y[s:s+block],zi=sosfilt(sos,x[s:s+block],axis=0,zi=zi)
    return y
def adsr(n,a,d,s,r,hold):
    t=np.arange(n)/SR; e=np.where(t<a,t/a,np.where(t<a+d,1-(1-s)*(t-a)/d,s)); return e*(1-np.clip((t-hold)/r,0,1))
def reverb(x,secs=2.6,decay=0.55,pre=0.02,tone=6500):
    n=int(SR*secs); t=np.arange(n)/SR; ir=rng.standard_normal((n,2))*np.exp(-t/decay)[:,None]; ir=lp(ir,tone); ir[:int(pre*SR)]=0; ir/=np.sqrt((ir**2).sum(0))
    return np.stack([fftconvolve(x[:,c],ir[:,c])[:N] for c in range(2)],1)
def grid(a,b,step):
    """times on the beat grid anchored at --groove, in [a,b)"""
    k=int(np.ceil((a-A.groove)/step-1e-9)); out=[]
    while A.groove+k*step<b-1e-6: out.append(A.groove+k*step); k+=1
    return out
def tt_(d): return np.arange(int(d*SR))/SR

# ======================= instruments =======================
def piano(m,d=2.6,vel=1.0):
    t=tt_(d); f=hz(m); s=np.zeros(len(t)); B=0.00035
    for h in range(1,11):
        fh=f*h*np.sqrt(1+B*h*h)
        if fh>16000: break
        a=(1/h**1.15)*(0.55+0.45*vel)**(h*0.3); dec=0.9+h*0.75+max(0,m-60)*0.04
        ph=rng.random()*6.28; s+=a*(np.sin(2*np.pi*fh*t+ph)+0.45*np.sin(2*np.pi*fh*1.0009*t+ph))*np.exp(-t*dec)
    ham=bp(rng.standard_normal(len(t)),800,4000)*np.exp(-t*280)*0.06
    s=(s*0.28+ham)*np.minimum(1,t/0.002)*np.clip((d-t)/0.25,0,1); return s*vel
def rhodes(m,d=1.8,vel=1.0):
    t=tt_(d); f=hz(m); I=(1.2+0.8*vel)*np.exp(-t*2.5); tine=0.5*vel*np.exp(-t*35)
    s=np.sin(2*np.pi*f*t+I*np.sin(2*np.pi*f*t)+tine*np.sin(2*np.pi*f*14*t))*np.exp(-t*1.1)*np.minimum(1,t/0.003)
    return s*np.clip((d-t)/0.2,0,1)*0.3*vel
def ensemble(m,d,att=0.5,rel=0.6,voices=6,det=0.10,vib=0.0015):
    t=tt_(d+rel); s=np.zeros(len(t))
    for v in range(voices):
        dd=det*(v/(voices-1)*2-1); f=hz(m)*2**(dd/12)*(1+vib*np.sin(2*np.pi*(4.8+0.3*v)*t+v))
        s+=sawtooth(np.cumsum(2*np.pi*f/SR)+rng.random()*6.28)
    return s/voices*adsr(len(t),att,0.3,0.85,rel,d)
def staccato(m,d=0.16):
    t=tt_(d+0.1); s=sum(sawtooth(2*np.pi*hz(m)*2**(x/12)*t+rng.random()*6) for x in (-0.08,0,0.08))/3
    return lp(s*adsr(len(t),0.008,0.05,0.6,0.08,d),3200)
def brass(m,d=0.9):
    t=tt_(d+0.3); s=sum(sawtooth(2*np.pi*hz(m)*2**(x/12)*t+rng.random()*6) for x in (-0.05,0,0.05))/3
    e=adsr(len(t),0.03,0.25,0.7,0.3,d); bright=np.exp(-t*4)
    return (lp(s,2600)*bright+lp(s,800)*(1-bright))*e
def marimba(m,d=0.9,vel=1.0):
    t=tt_(d); f=hz(m); s=np.sin(2*np.pi*f*t)*np.exp(-t*5)+0.35*np.sin(2*np.pi*f*3.93*t)*np.exp(-t*14)+0.12*np.sin(2*np.pi*f*9.2*t)*np.exp(-t*32)
    return (s+bp(rng.standard_normal(len(t)),2000,6000)*np.exp(-t*400)*0.08)*np.minimum(1,t/0.001)*0.5*vel
def glass(m,d=1.6,g=1.0):
    t=tt_(d); f=hz(m); I=1.4*np.exp(-t*5); return np.sin(2*np.pi*f*t+I*np.sin(2*np.pi*f*2.76*t))*np.exp(-t*2.2)*np.minimum(1,t/0.002)*g*0.5
def kick(g=1.0,soft=False):
    t=tt_(0.45); f=(45 if soft else 45)+(70 if soft else 110)*np.exp(-t*(25 if soft else 35)); s=np.tanh(1.6*np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*(9 if soft else 7.5)))
    if not soft: s=s+rng.standard_normal(len(t))*np.exp(-t*600)*0.25
    return s*g
def snare(g=1.0,tone=190):
    t=tt_(0.3); return (np.sin(2*np.pi*tone*t)*np.exp(-t*28)*0.6+bp(rng.standard_normal(len(t)),1200,7000)*np.exp(-t*20))*g
def rim(g=1.0):
    t=tt_(0.06); return (np.sin(2*np.pi*1750*t)*0.6+bp(rng.standard_normal(len(t)),2000,6000))*np.exp(-t*220)*g
def shaker(g=1.0):
    t=tt_(0.09); e=np.minimum(1,t/0.012)*np.exp(-t*45); return hp(rng.standard_normal(len(t)),5000)*e*g
def hat(g=1.0,open_=False):
    t=tt_(0.3 if open_ else 0.05); return hp(rng.standard_normal(len(t)),7000)*np.exp(-t*(12 if open_ else 110))*g
def taiko(g=1.0):
    t=tt_(1.0); f=55+70*np.exp(-t*12); return (np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*4.5)+lp(rng.standard_normal(len(t)),900)*np.exp(-t*30)*0.5)*g
def boom(g=1.0,dec=2.6):
    t=tt_(3.0); f=30+60*np.exp(-t*6); return (np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*dec)*0.5+lp(rng.standard_normal(len(t)),2500)*np.exp(-t*5)*0.4)*g
def swell(d=1.2,lo=3000):
    t=tt_(d); return hp(rng.standard_normal(len(t)),lo)*(t/d)**3
def riser(d,g=1.0):
    t=tt_(d); nz=rng.standard_normal(len(t)); out=np.zeros(len(t))
    for s in range(0,len(t),1024):
        c=300+8000*((s/SR)/d)**2; out[s:s+1024]=bp(nz[s:s+1024],c*0.7,c*1.4)
    return out*(t/d)**2.2*g
def sub(m,d,g=1.0):
    t=tt_(d); return np.sin(2*np.pi*hz(m)*t)*adsr(len(t),0.01,0.1,0.85,0.08,d-0.08)*g
def sidechain(times,depth=0.5,rel=0.12):
    sc=np.ones(N)
    for k in times:
        i0=int(k*SR); i1=min(N,i0+int(0.4*SR)); t=np.arange(i1-i0)/SR; sc[i0:i1]=np.minimum(sc[i0:i1],1-depth*np.exp(-t/rel))
    return sc[:,None]
def chord_seq(CH):
    return lambda t: CH[int(max(0,t)/BAR)%len(CH)]

# ======================= styles =======================
def style_piano():
    CH=[([53,60,64,67],41),([50,57,60,65],38),([46,53,57,62],34),([48,55,60,64],36)]   # Fadd9 Dm7 Bbadd9 Csus-ish (I vi IV V)
    ch=chord_seq(CH); S={k:z() for k in ('piano','strings','bass','perc','fx')}
    # hook: sparse high notes, tension
    for i,(tm,m) in enumerate([(0.15,84),(0.9,81),(1.6,79),(2.2,77),(2.7,76),(3.05,74)]): add(S['piano'],tm,mono2(piano(m,1.8,0.55),0.3*(-1)**i))
    add(S['strings'],0.0,mono2(ensemble(65,A.hit,att=2.5,rel=0.3)*0.5,-0.2)); add(S['strings'],0.0,mono2(ensemble(72,A.hit,att=3.0,rel=0.3)*0.35,0.2))
    add(S['fx'],A.hit-1.3,mono2(swell(1.3,2500)*0.5))
    # hit: low chord + boom
    for m in (29,41,48,53,57,60,65): add(S['piano'],A.hit,mono2(piano(m,3.5,1.0),(m-50)/40))
    add(S['fx'],A.hit,mono2(boom(0.6,3.2)))
    # pad strings from groove
    for b in range(int(A.groove/BAR),int(A.drop/BAR)+1):
        t0=max(A.groove,b*BAR); notes,root=CH[b%len(CH)]
        for m in notes: add(S['strings'],t0,mono2(ensemble(m,BAR,0.6,0.7)*0.22,(m-58)/20))
    # broken chords: 8ths in groove, 8ths + octave in main
    pat=[0,2,1,3,2,1,3,1]
    for k,t in enumerate(grid(A.groove,A.drop,BEAT/2)):
        notes,root=ch(t); ns=sorted(notes)+[sorted(notes)[0]+12]
        m=ns[pat[k%8]%len(ns)]+12; vel=0.55 if t<A.main else 0.7
        add(S['piano'],t,mono2(piano(m,1.4,vel),0.25*np.sin(k*0.6)))
        if k%8==0: add(S['piano'],t,mono2(piano(root+12,2.2,0.75)))
    # melody in peak (and every other bar in main)
    mel=[(0,77),(1,76),(1.5,74),(2,72),(3,74)]
    for b in range(int(np.ceil(A.main/BAR)),int(A.drop/BAR)):
        bt=b*BAR
        if bt>=A.peak-1e-6 or b%2==1:
            for off,m in mel: add(S['piano'],bt+off*BEAT,mono2(piano(m+12,1.6,0.9 if bt>=A.peak else 0.75),0.1))
    # heartbeat kick + shaker in main; bass
    for t in grid(A.main,A.drop,BEAT):
        bi=int(round((t-A.groove)/BEAT))
        if bi%2==0: add(S['perc'],t,mono2(kick(0.55,soft=True)))
    for t in grid(A.groove,A.drop,BEAT/2): add(S['perc'],t+BEAT/4,mono2(shaker(0.35 if t>=A.main else 0.22),0.3))
    for t in grid(A.groove,A.drop,BEAT*2): notes,root=ch(t); add(S['bass'],t,mono2(sub(root+12,BEAT*2-0.05,0.55 if t<A.main else 0.85)))
    add(S['fx'],A.peak-1.2,mono2(swell(1.2,4000)*0.3)); add(S['fx'],A.end-(A.end-A.drop),mono2(swell(A.end-A.drop,3000)*0.4))
    for m in (29,41,53,57,60,64,67,72): add(S['piano'],A.end,mono2(piano(m,3.4,1.0),(m-55)/40))
    for m in (53,60,65,69): add(S['strings'],A.end,mono2(ensemble(m,2.6,0.05,1.0)*0.25,(m-60)/20))
    S['strings']=lp(hp(S['strings'],180),3500)
    return S,{'piano':0.62,'strings':0.55,'bass':0.7,'perc':0.5,'fx':0.5},{'piano':0.45,'strings':0.5,'perc':0.15,'fx':0.4},(3.0,0.75)

def style_lofi():
    CH=[([62,65,69,72,76],50),([59,65,67,71],43),([60,64,67,71,74],48),([57,60,64,67],45)]   # Dm9 G13 Cmaj9 Am7
    ch=chord_seq(CH); S={k:z() for k in ('keys','drums','bass','fx')}; SW=BEAT*0.08   # swing offset on off-8ths
    # hook: filtered keys + clock ticks
    for i,t in enumerate(np.arange(0.1,A.hit-0.25,BEAT/2)): add(S['fx'],t,mono2(rim(0.18+0.25*t/A.hit),0.4*(-1)**i))
    for m in CH[0][0]: add(S['keys'],0.05,mono2(rhodes(m-12+12,A.hit,0.6)))
    add(S['fx'],A.hit-1.2,mono2(swell(1.2,2000)*0.4))
    for m in (50,57,62,65,69,72): add(S['keys'],A.hit,mono2(rhodes(m,2.6,1.0),(m-62)/25))
    add(S['drums'],A.hit,mono2(kick(0.9)))
    # chords: comp pattern (beat 1 and the 'and' of 2), swung
    for b in range(int(np.ceil(A.groove/BAR-1e-9)),int(A.drop/BAR)+1):
        bt=A.groove+(b-int(np.ceil(A.groove/BAR-1e-9)))*BAR
        if bt>=A.drop: break
        notes,root=ch(bt)
        gv=0.6 if bt<A.main else 1.0
        for off,dur,v in ((0,BEAT*1.4,0.85*gv),(BEAT*1.5+SW,BEAT*1.2,0.6*gv),(BEAT*3+SW,BEAT*0.9,0.5*gv)):
            for i,m in enumerate(notes): add(S['keys'],bt+off+i*0.012,mono2(rhodes(m,dur+0.4,v),(m-64)/25))
        add(S['bass'],bt,mono2(sub(root,BEAT*1.8,0.75*gv))); add(S['bass'],bt+BEAT*2.5+SW,mono2(sub(root+7,BEAT*1.2,0.55*gv)))
    # boom-bap from groove (light) -> main (full)
    for t in grid(A.groove,A.drop,BEAT/2):
        k=int(round((t-A.groove)/(BEAT/2)))%8; sw=SW if k%2 else 0; full=t>=A.main
        if k in (0,5) or (full and k==3 and False): add(S['drums'],t+sw,mono2(kick(0.8 if full else 0.55,soft=not full)))
        if k in (2,6) and full: add(S['drums'],t,mono2(snare(0.55),0.05))
        if k in (2,6) and not full: add(S['drums'],t,mono2(rim(0.35),0.1))
        add(S['drums'],t+sw,mono2(hat((0.28 if k%2==0 else 0.18)*(1 if full else 0.6)),0.25))
    # lead: rhodes high motif in peak
    for b in range(int(np.ceil(A.peak/BAR-1e-9))*1,int(A.drop/BAR)+1):
        bt=b*BAR
        if A.peak-1e-6<=bt<A.drop:
            for off,m in ((0,79),(0.75,76),(1.5,74),(2.5,72)): add(S['keys'],bt+off*BEAT,mono2(rhodes(m,1.0,0.9),0.2))
    for m in (48,55,59,62,64,67,71): add(S['keys'],A.end+((m-48)*0.01),mono2(rhodes(m,3.0,0.95),(m-60)/25))
    # vinyl crackle + tape
    cr=np.zeros(N); idx=rng.random(N)<0.0007; cr[idx]=rng.standard_normal(idx.sum())*0.6; cr=bp(cr,1500,8000)+lp(rng.standard_normal(N),4000)*0.012
    S['fx']+=mono2(cr*0.35)
    return S,{'keys':0.6,'drums':0.55,'bass':0.5,'fx':0.45},{'keys':0.3,'drums':0.12,'fx':0.2},(1.8,0.5)

def style_cinematic():
    CH=[([50,57,62,65],38),([46,53,58,62],34),([53,57,60,65],41),([48,55,60,64],36)]   # Dm Bb F C
    ch=chord_seq(CH); S={k:z() for k in ('strings','ostinato','brass','drums','fx')}
    # hook: low drone + pulse + riser
    add(S['strings'],0,mono2(ensemble(50,A.hit,att=1.5,rel=0.2)*0.35)); add(S['strings'],0,mono2(ensemble(50,A.hit,att=2.5,rel=0.2)*0.4))
    for t in np.arange(0.2,A.hit-0.2,BEAT): add(S['drums'],t,mono2(hp(taiko(0.12+0.25*t/A.hit),70)))
    add(S['fx'],A.hit-2.0,mono2(riser(2.0,0.6))); add(S['fx'],A.hit-1.0,mono2(swell(1.0)*0.5))
    add(S['fx'],A.hit,mono2(boom(1.0,1.8))); add(S['drums'],A.hit,mono2(taiko(1.2)))
    for m in (38,50,57,62): add(S['brass'],A.hit,mono2(brass(m,1.4)*0.9,(m-50)/30))
    # pads
    for b in range(int(A.groove/BAR),int(A.drop/BAR)+1):
        t0=max(A.groove,b*BAR); notes,root=CH[b%len(CH)]
        for m in notes: add(S['strings'],t0,mono2(ensemble(m,BAR,0.4,0.6)*0.2,(m-55)/20))
        add(S['strings'],t0,mono2(ensemble(root,BAR,0.3,0.5)*0.35))
    # ostinato 8ths (groove) -> 16ths (main)
    pat=[0,0,2,0,1,0,2,3]
    for k,t in enumerate(grid(A.groove,A.drop,BEAT/2)):
        notes,root=ch(t); m=sorted(notes)[pat[k%8]%len(notes)]; acc=1.0 if k%4==0 else 0.7
        add(S['ostinato'],t,mono2(staccato(m,0.16)*acc,-0.35)); add(S['ostinato'],t,mono2(staccato(m+12,0.14)*acc*0.6,0.35))
        if t>=A.main: add(S['ostinato'],t+BEAT/4,mono2(staccato(m+12,0.12)*0.5,0.0))
    # drums: taiko pattern in main, toms build in lift
    for t in grid(A.main,A.drop,BEAT):
        bi=int(round((t-A.groove)/BEAT))%4
        if bi in (0,2): add(S['drums'],t,mono2(hp(taiko(0.75 if bi==0 else 0.5),60)))
        if bi==3: add(S['drums'],t+BEAT/2,mono2(taiko(0.45),0.3))
        add(S['drums'],t+BEAT/2,mono2(hat(0.12),-0.3))
    for k,t in enumerate(grid(A.lift,A.peak,BEAT/4)): add(S['drums'],t,mono2(taiko(0.2+0.5*k/16),0.4*np.sin(k)))
    # brass stabs on bar starts at peak
    for t in grid(A.peak,A.drop,BAR/2):
        notes,root=ch(t)
        for m in (root+12,)+tuple(notes[:3]): add(S['brass'],t,mono2(brass(m,0.6)*0.6,(m-50)/30))
    add(S['fx'],A.lift,mono2(riser(A.peak-A.lift,0.3)))
    add(S['fx'],A.drop,mono2(swell(A.end-A.drop,2000)*0.7)); add(S['fx'],A.end,mono2(boom(1.0,1.5))); add(S['drums'],A.end,mono2(taiko(1.3)))
    for m in (38,50,53,57,62,65): add(S['brass'],A.end,mono2(brass(m,2.2)*0.8,(m-55)/30)); add(S['strings'],A.end,mono2(ensemble(m,2.6,0.05,0.9)*0.25))
    S['strings']=lp(S['strings'],3000); S['ostinato']=hp(S['ostinato'],150)
    return S,{'strings':0.55,'ostinato':0.55,'brass':0.45,'drums':0.5,'fx':0.45},{'strings':0.5,'ostinato':0.35,'brass':0.5,'drums':0.35,'fx':0.4},(3.2,0.8)

def style_minimal():
    CH=[([60,64,67,71],48),([57,60,64,67,71],45),([53,57,60,64],41),([55,59,62,64],43)]   # Cmaj7 Am9 Fmaj7 G6
    ch=chord_seq(CH); S={k:z() for k in ('mallet','bell','pad','perc','bass','fx')}
    for i,t in enumerate(np.arange(0.1,A.hit-0.2,BEAT/2)): add(S['perc'],t,mono2(rim(0.15+0.3*t/A.hit),0.5*(-1)**i))
    for i,m in enumerate((79,76,72,71,67)): add(S['bell'],0.4+i*0.55,mono2(glass(m,1.4,0.5),0.4*(-1)**i))
    add(S['fx'],A.hit-1.0,mono2(swell(1.0,4000)*0.35))
    for i,m in enumerate((84,88,91,95)): add(S['bell'],A.hit+i*0.045,mono2(glass(m,2.2,0.8),(i-1.5)/2))
    add(S['bass'],A.hit,mono2(sub(36,1.2,0.6)))
    # airy pad
    for b in range(int(A.groove/BAR),int(A.drop/BAR)+1):
        t0=max(A.groove,b*BAR); notes,root=CH[b%len(CH)]
        for m in notes: add(S['pad'],t0,mono2(ensemble(m+12,BAR,0.8,0.8,voices=4,det=0.06)*0.12,(m-62)/20))
    # marimba arp 8ths (groove) / 16ths with rests (main)
    pat=[0,2,3,1,2,0,3,2]
    for k,t in enumerate(grid(A.groove,A.drop,BEAT/4)):
        notes,root=ch(t); full=t>=A.main
        if not full and k%2: continue
        if full and k%8 in (3,7): continue
        m=sorted(notes)[pat[k%8]%len(notes)]+12; add(S['mallet'],t,mono2(marimba(m,0.8,0.85 if k%4==0 else 0.6),0.4*np.sin(k*0.9)))
    # bell motif every other bar in main, every bar in peak
    for b in range(int(np.ceil(A.main/BAR)),int(A.drop/BAR)):
        bt=b*BAR
        if bt>=A.peak-1e-6 or b%2==0:
            for off,m in ((0,88),(1.5,84),(2,86),(3,83)): add(S['bell'],bt+off*BEAT,mono2(glass(m,1.3,0.55),0.25))
    # pulse: sub kick on 1&3 + rim on 2&4 + ticks
    for t in grid(A.main,A.drop,BEAT):
        bi=int(round((t-A.groove)/BEAT))%4
        if bi in (0,2): add(S['perc'],t,mono2(kick(0.5,soft=True)))
        else: add(S['perc'],t,mono2(rim(0.35),0.15))
    for t in grid(A.groove,A.drop,BEAT/2): add(S['perc'],t+BEAT/4,mono2(hat(0.16),-0.35))
    for t in grid(A.main,A.drop,BEAT*2): notes,root=ch(t); add(S['bass'],t,mono2(sub(root,BEAT*2-0.05,0.55)))
    add(S['fx'],A.drop,mono2(swell(A.end-A.drop,4000)*0.4))
    for i,m in enumerate((72,76,79,83,86,91)): add(S['bell'],A.end+i*0.05,mono2(glass(m,2.6,0.75),(i-2.5)/3))
    for m in (60,64,67,71): add(S['pad'],A.end,mono2(ensemble(m+12,2.6,0.05,1.0,voices=4,det=0.06)*0.18))
    add(S['bass'],A.end,mono2(sub(48,1.2,0.35)))
    S['pad']=lp(hp(S['pad'],300),5000)
    return S,{'mallet':0.55,'bell':0.32,'pad':0.5,'perc':0.5,'bass':0.42,'fx':0.4},{'mallet':0.35,'bell':0.55,'pad':0.5,'perc':0.15,'fx':0.4},(3.4,0.85)

S,gains,sends,(rv_secs,rv_decay)=dict(piano=style_piano,lofi=style_lofi,cinematic=style_cinematic,minimal=style_minimal)[A.style]()
# duck pads/keys a little on kicks for groove styles
mix=sum(S[k]*g for k,g in gains.items())
wet=reverb(sum(S[k]*gains[k]*sends.get(k,0) for k in S),rv_secs,rv_decay)
mix=hp(mix+wet*0.6,30)
if A.style=='lofi':   # tape: warm top, gentle wow
    mix=lp(mix,7000); wow=1+0.002*np.sin(2*np.pi*0.6*T); idx=np.clip((np.arange(N)*wow).astype(int),0,N-1); mix=mix[idx]
mid=(mix[:,0]+mix[:,1])/2; side=hp((mix[:,0]-mix[:,1])/2,300)*1.2; mix=np.stack([mid+side,mid-side],1)
rms=np.sqrt(np.convolve((mix**2).mean(1),np.ones(2048)/2048,'same'))+1e-9; lvl=20*np.log10(rms); peak=np.percentile(lvl,95)
mix*=10**(np.where(lvl>peak-6,(peak-6-lvl)*0.35,0)/20)[:,None]
dyn=np.interp(T,[0,A.hit-0.01,A.hit,A.groove,A.main-0.01,A.main,A.lift,A.peak,A.drop,A.drop+0.01,A.end-0.01,A.end,A.dur],[0.8,1.0,1.0,0.78,0.78,0.85,0.85,1.0,1.0,0.7,0.8,1.0,1.0])
mix*=(dyn*np.clip((A.dur-T)/1.2,0,1)*np.minimum(1,T/0.05))[:,None]
mix/=np.max(np.abs(mix))+1e-9; mix=np.tanh(mix*1.5)/np.tanh(1.5)*0.89
d=(np.clip(mix[:int(A.dur*SR)],-1,1)*32767).astype(np.int16)
w=wave.open(A.out,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes()); w.close()
normalize(A.out); print(f'music[{A.style}] ->',A.out)
