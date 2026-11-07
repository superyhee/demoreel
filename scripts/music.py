#!/usr/bin/env python3
"""PLACEHOLDER background music (synthesized pad + pluck arp + soft kick). Amateur-sounding by design —
replace with licensed music for anything published. Use it so timing/ducking can be reviewed early.
usage: music.py <out.wav> [duration=30] [bpm=120] [beat_start=5.0] [beat_end=duration-4] [impact=3.6]
  beat_start: when drums/arp enter (usually when the product UI appears); impact: logo hit time."""
import sys, wave
import numpy as np
out_path=sys.argv[1]; T=float(sys.argv[2]) if len(sys.argv)>2 else 30; bpm=float(sys.argv[3]) if len(sys.argv)>3 else 120
b0=float(sys.argv[4]) if len(sys.argv)>4 else 5.0; b1=float(sys.argv[5]) if len(sys.argv)>5 else T-4; imp=float(sys.argv[6]) if len(sys.argv)>6 else 3.6
sr=44100; n=int(sr*(T+0.5)); t=np.arange(n)/sr; out=np.zeros(n); rng=np.random.default_rng(1)
note=lambda m:440*2**((m-69)/12)
chords=[[57,60,64],[53,57,60],[48,52,55,60],[55,59,62]]  # Am F C G
beat=60/bpm; bar=4*beat
for i in range(int(T/bar)+1):
    s=i*bar; idx=(t>=s)&(t<s+bar+0.3); tt=t[idx]-s; env=np.minimum(1,tt/0.4)*np.exp(-np.maximum(0,tt-bar)/0.15)
    for m in chords[i%4]:
        f=note(m); out[idx]+=0.05*env*(np.sin(2*np.pi*f*tt)+0.3*np.sin(2*np.pi*2*f*tt+0.5)+0.2*np.sin(2*np.pi*f*1.003*tt))
k=0; s=b0
while s<b1+0.4:
    ch=chords[int(s/bar)%4]; m=ch[k%len(ch)]+12+(12 if k%8==7 else 0); idx=(t>=s)&(t<s+0.6); tt=t[idx]-s
    out[idx]+=0.06*np.exp(-tt*7)*np.sin(2*np.pi*note(m)*tt)*(1+0.5*np.sin(2*np.pi*note(m)*2*tt)); s+=beat/2; k+=1
def kick(s,a):
    idx=(t>=s)&(t<s+0.35); tt=t[idx]-s; f=50+90*np.exp(-tt*30); out[idx]+=a*np.exp(-tt*9)*np.sin(2*np.pi*np.cumsum(f)/sr)
b=b0
while b<b1: kick(b,0.35); b+=beat
b=b0+beat/2
while b<b1:
    idx=(t>=b)&(t<b+0.05); out[idx]+=0.025*rng.standard_normal(idx.sum())*np.exp(-(t[idx]-b)*90); b+=beat
idx=(t>=imp-1.6)&(t<imp); tt=t[idx]-(imp-1.6); out[idx]+=0.08*(tt/1.6)**2*rng.standard_normal(idx.sum())
kick(imp,0.6); kick(b1+0.6,0.5)
out*=np.minimum(1,t/0.2)*np.clip((T+0.3-t)/1.5,0,1); out=out/np.max(np.abs(out))*0.8
d=(np.stack([out,np.roll(out,200)],1)*32767).astype(np.int16)
w=wave.open(out_path,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(d.tobytes()); w.close(); print('music ->',out_path)
