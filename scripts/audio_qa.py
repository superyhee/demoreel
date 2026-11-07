#!/usr/bin/env python3
"""Numeric audio QA for a music bed against a VO track (replicates mix.sh ducking).
usage: audio_qa.py <music.wav> <vo.wav> [--gain 0.18] [--cues 3.55,5,9,21,23,26,26.6]
Prints: integrated-ish level, section RMS arc, sub(<120Hz) share, speech-band SNR (median/p5/min), clipping."""
import sys, wave, subprocess, tempfile, argparse, os
import numpy as np
from scipy.signal import butter, sosfilt
a=argparse.ArgumentParser(); a.add_argument('music'); a.add_argument('vo'); a.add_argument('--gain',type=float,default=0.18); a.add_argument('--cues',default='3.55,5,9,21,23,26,26.6')
o=a.parse_args(); hit,gr,mn,lf,pk,dr,en=map(float,o.cues.split(',')); sr=44100
def L(p):
    w=wave.open(p); x=np.frombuffer(w.readframes(w.getnframes()),np.int16).reshape(-1,w.getnchannels()).astype(float)/32768; return x
d=tempfile.mkdtemp(); duck=os.path.join(d,'duck.wav'); vo16=os.path.join(d,'vo.wav')
subprocess.run(['ffmpeg','-v','error','-y','-i',o.vo,'-i',o.music,'-filter_complex',
 f"[0]volume=1.6,asplit[v1][v2];[v2]atrim=start=0.15,asetpts=PTS-STARTPTS,apad[v2a];[1]volume={o.gain},equalizer=f=2500:t=q:w=1.2:g=-4[m];[m][v2a]sidechaincompress=threshold=0.015:ratio=10:attack=8:release=450:knee=4[md]",
 '-map','[md]',duck,'-map','[v1]',vo16],check=True)
x=L(o.music); m=x.mean(1); lo=sosfilt(butter(4,120,'low',fs=sr,output='sos'),m)
print(f'peak {np.abs(x).max():.2f}  clip% {(np.abs(x)>0.99).mean()*100:.3f}  LRcorr {np.corrcoef(x[:,0],x[:,1])[0,1]:.2f}')
arc=[]
for a_,b_,n in [(0,hit,'hook'),(gr,mn,'groove'),(mn,lf,'main'),(pk,dr,'peak'),(en,en+3,'end')]:
    s=slice(int(a_*sr),int(b_*sr)); e=(m[s]**2).sum()+1e-12; arc.append(f'{n} {10*np.log10((m[s]**2).mean()+1e-12):.1f}dB/sub{100*(lo[s]**2).sum()/e:.0f}%')
print('arc:',' | '.join(arc))
band=butter(4,[300,4000],'band',fs=sr,output='sos'); vo=sosfilt(band,L(vo16).mean(1)); mu=sosfilt(band,L(duck).mean(1)); win=4410
n=min(len(vo),len(mu)); rv=np.array([np.sqrt((vo[i:i+win]**2).mean()) for i in range(0,n-win,win)]); rm=np.array([np.sqrt((mu[i:i+win]**2).mean()) for i in range(0,n-win,win)])
act=rv>np.percentile(rv[rv>0],60)*0.3; snr=20*np.log10(rv[act]/(rm[act]+1e-9))
print(f'speech SNR: median {np.median(snr):.1f}  p5 {np.percentile(snr,5):.1f}  min {snr.min():.1f} dB')
