# Audio QA without listening

Claude can't hear the mix — verify with numbers, then tell the user what you measured and that they should listen.

1. **Loudness**: `ffmpeg -i out.mp4 -af ebur128=peak=true:framelog=quiet -f null -` → I ≈ -16 LUFS, Peak ≤ -1 dBFS.
2. **Section arc** (music alone): RMS per section should rise hook < groove < main < lift < peak, dip at drop.
   Typical good result: hook -20, groove -18, main -13, peak -11.5 dB.
3. **Low-end share** (<120 Hz energy / total) per section: 30–40 %. >50 % = muddy/boomy (cut sub bass, impact boom, kick).
4. **Speech-band SNR** (most important): render the ducked music bed exactly as mix.sh does, band-pass VO and music
   300–4000 Hz, 100 ms windows, keep windows where VO is active. Targets: median ≥ 15 dB, p5 ≥ 10 dB.
   Dips that line up with VO line onsets = ducking reacts too late → lookahead sidechain (already in mix.sh).
   Dips mid-line = an arrangement element (riser, snare roll, lead) fights the voice → lower it in music_pro.py.
5. **Clicks**: largest sample-to-sample jumps; acceptable only at intentional transients (risers into hits, impacts).
6. **Spectrogram** for a visual sanity check:
   `ffmpeg -i music.wav -lavfi "showspectrumpic=s=1600x500:legend=1:fscale=log" spec.png` (auto-scaled — don't judge level from it).

Snippet (speech-band SNR):
```python
from scipy.signal import butter, sosfilt
band=butter(4,[300,4000],'band',fs=44100,output='sos'); vo=sosfilt(band,vo); mu=sosfilt(band,ducked_music)
win=4410; rv=rms_windows(vo,win); rm=rms_windows(mu,win); act=rv>np.percentile(rv[rv>0],60)*0.3
snr=20*np.log10(rv[act]/(rm[act]+1e-9)); print(np.median(snr), np.percentile(snr,5))
```
