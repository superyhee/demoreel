#!/usr/bin/env python3
"""Beat grid for cutting on the music → site/beats.js (window.BEATS), picked up by engine.js like subs.js.
The engine snaps camera-move ARRIVALS and headline starts to the nearest beat (DEMO beatSnap), H.beat / H.pulse expose it.

usage:
  beat_grid.py beats.js --bpm 120 --start 5.0 --dur 30      # procedural score (music_pro.py / music_styles.py): exact grid
      the grid is anchored at 0 s like the scores' bars; --start drops beats before it (e.g. the --groove cue).
      Keep the score's cues ON that grid (multiples of 60/bpm) — e.g. at 90 BPM --groove 5.0 is half a beat off → use 5.33
  beat_grid.py beats.js --wav music.wav [--offset 0]        # licensed / generated track: detect tempo + phase (numpy only)
      --offset = where the track starts in the film (mix.sh places music at 0 unless you pre-pad it)
Output: window.BEATS={bpm, beats:[t…], down:[t…] (bar starts, 4/4), src}. Prints the grid summary.
"""
import argparse, json, os, sys, wave
import numpy as np

def read_wav(path):
    with wave.open(path, 'rb') as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    if sw != 2: sys.exit('beat_grid: 16-bit PCM wav expected (ffmpeg -i in.mp3 -ac 2 -ar 44100 -sample_fmt s16 music.wav)')
    x = np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1, ch).mean(1) / 32768
    return x, sr

HOP, NFFT = 512, 2048

def onset_env(x, sr, hop=HOP, nfft=NFFT):
    """spectral flux on a log-magnitude STFT (half-wave rectified) → (full-band env, low-band env <200 Hz), one value per hop.
    Index i is centred at i*hop + nfft/2 samples (see t_of)."""
    win = np.hanning(nfft).astype(np.float32); n = 1 + max(0, len(x) - nfft) // hop
    fr = np.lib.stride_tricks.as_strided(x, (n, nfft), (x.strides[0] * hop, x.strides[0])) * win
    S = np.log1p(100 * np.abs(np.fft.rfft(fr, axis=1)))
    F = np.vstack([np.zeros(S.shape[1]), np.maximum(0, np.diff(S, axis=0))])
    lo = int(200 * nfft / sr)
    def clean(e): e = e - np.convolve(e, np.ones(16) / 16, 'same'); return np.maximum(e, 0)   # drop slow loudness changes
    return clean(F.sum(1)), clean(F[:, 1:lo].sum(1)), sr / hop

def t_of(i, sr): return (np.asarray(i) * HOP + NFFT / 2) / sr

def detect(x, sr, lo=70, hi=180):
    env, low, fps = onset_env(x, sr)
    ac = np.correlate(env, env, 'full')[len(env) - 1:]
    lags = np.arange(len(ac)); bpm = 60 * fps / np.maximum(lags, 1)
    ok = (bpm >= lo) & (bpm <= hi)
    w = np.exp(-0.5 * (np.log2(bpm / 120) / 0.9) ** 2)            # mild prior towards ~120 BPM (resolves half/double)
    lag = lags[ok][np.argmax((ac * w)[ok])]
    # refine the period to sub-hop precision with a parabola through the peak
    a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]; lagf = lag + 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) else lag
    period = lagf / fps
    # phase from the LOW band (kick / bass): full-band flux is dominated by hats, claps and shakers that often sit on the
    # off-beat. Comb = every period from offset p; the offset collecting the most low-band onset energy wins.
    nlo = int(200 * NFFT / sr) - 1
    ph_env = low if low.sum() / nlo > 0.05 * env.sum() / (NFFT // 2) else env   # per-bin energy: is there a real low end?
    idx = lambda ts: np.clip(np.round((ts * sr - NFFT / 2) / HOP).astype(int), 0, len(ph_env) - 1)   # inverse of t_of
    # joint fine search: period within ±4 % of the autocorrelation estimate (swing / odd meters bias it) × 100 phases
    dur = len(x) / sr; best = (-1, period, 0.0)
    for P in np.linspace(period * 0.96, period * 1.04, 81):
        for p in np.linspace(0, P, 100, endpoint=False):
            sc = ph_env[idx(np.arange(p, dur, P))].mean()   # mean, not sum: shorter periods must not win by having more taps
            if sc > best[0]: best = (sc, P, p)
    _, period, p0 = best
    beats = np.arange(p0, dur, period)
    # downbeat: of the 4 possible bar phases, the one with the strongest low-band onsets
    sums = [ph_env[idx(beats[k::4])].sum() for k in range(4)]
    return 60 / period, beats, int(np.argmax(sums))

def main():
    a = argparse.ArgumentParser(); a.add_argument('out')
    a.add_argument('--bpm', type=float); a.add_argument('--start', type=float, default=0.0); a.add_argument('--dur', type=float, default=30)
    a.add_argument('--wav'); a.add_argument('--offset', type=float, default=0.0); o = a.parse_args()
    if o.wav:
        x, sr = read_wav(o.wav); bpm, beats, d0 = detect(x, sr); beats = beats + o.offset; src = os.path.basename(o.wav)
        down = beats[d0::4]
    elif o.bpm:
        bpm = o.bpm; g = np.arange(0, o.dur + 1e-6, 60 / bpm); beats = g[g >= o.start - 1e-6]; down = g[::4][g[::4] >= o.start - 1e-6]
        src = f'grid {bpm:g} BPM from {o.start:g} s'
    else:
        sys.exit('give --bpm (procedural score) or --wav (detect from audio)')
    B = {'bpm': round(float(bpm), 2), 'beats': [round(float(t), 3) for t in beats if t >= 0],
         'down': [round(float(t), 3) for t in down if t >= 0], 'src': src}
    with open(o.out, 'w') as fh: fh.write('window.BEATS=' + json.dumps(B) + ';\n')
    print(f"{o.out}: {B['bpm']} BPM, {len(B['beats'])} beats from {B['beats'][0] if B['beats'] else '-'} s ({src})")

if __name__ == '__main__':
    main()
