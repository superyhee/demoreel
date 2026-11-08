#!/usr/bin/env python3
"""One voice-over entry point for many TTS engines → a timed WAV + a per-line manifest (for align_subs.py subtitles).

usage: tts.py vo.tsv out.wav --provider P [--voice V] [--lang L] [--duration S] [--model M] [--instructions "…"]
  vo.tsv lines: <start seconds><TAB><text>
  P = polly | azure | elevenlabs | openai | kokoro | say          (setup + voices: docs/voiceover.md)
Writes out.wav (stereo 44.1 kHz, every line placed at its start) and out.manifest.json [{start,dur,text,clip}], clips in out_clips/.
Then: align_subs.py out.manifest.json site/subs.json --lang zh   → word-timed subtitles for ANY provider.

Credentials come ONLY from environment variables and are never printed or written:
  polly: AWS CLI credentials (AWS_PROFILE / SSO), POLLY_REGION      azure: AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
  elevenlabs: ELEVENLABS_API_KEY                                     openai: OPENAI_API_KEY
  kokoro: local model (pip install kokoro "misaki[zh]" soundfile; first run downloads ~330 MB from Hugging Face)
  say: macOS `say` / Linux `espeak-ng` (offline, robotic — drafts only)
"""
import argparse, json, os, subprocess, sys, tempfile, wave, urllib.request, urllib.error, html
import numpy as np

SR = 44100
DEFAULT_VOICE = {   # (zh, en)
    'polly': ('Zhiyu', 'Ruth'), 'azure': ('zh-CN-XiaoxiaoNeural', 'en-US-AvaMultilingualNeural'),
    'elevenlabs': ('21m00Tcm4TlvDq8ikWAM', '21m00Tcm4TlvDq8ikWAM'), 'openai': ('coral', 'coral'),
    'kokoro': ('zf_xiaoxiao', 'af_heart'), 'say': ('Tingting', 'Samantha')}

def need(var):
    v = os.environ.get(var)
    if not v: sys.exit(f'ERROR: set {var} in your environment (see docs/voiceover.md) — keys are never read from files in this repo')
    return v

def http(url, body, headers, timeout=60):
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f'ERROR: {url.split("/")[2]} returned HTTP {e.code}: {e.read()[:300].decode("utf-8", "ignore")}')

def synth(p, text, o, path):
    zh = o.lang.lower().startswith(('zh', 'cmn'))
    voice = o.voice or DEFAULT_VOICE[p][0 if zh else 1]
    if p == 'polly':
        region = os.environ.get('POLLY_REGION', os.environ.get('AWS_REGION', 'us-east-1'))
        cmd = ['aws', 'polly', 'synthesize-speech', '--region', region, '--engine', o.model or 'neural', '--voice-id', voice,
               '--output-format', 'mp3', '--sample-rate', '24000', '--text', text]
        if o.lang: cmd += ['--language-code', {'zh': 'cmn-CN', 'en': 'en-US'}.get(o.lang, o.lang)]
        r = subprocess.run(cmd + [path], capture_output=True, text=True)
        if r.returncode: sys.exit('ERROR: polly: ' + r.stderr.strip()[:300])
    elif p == 'azure':
        key, region = need('AZURE_SPEECH_KEY'), need('AZURE_SPEECH_REGION')
        loc = 'zh-CN' if zh else 'en-US'
        ssml = f"<speak version='1.0' xml:lang='{loc}'><voice name='{voice}'>{html.escape(text)}</voice></speak>"
        open(path, 'wb').write(http(f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1', ssml.encode(),
            {'Ocp-Apim-Subscription-Key': key, 'Content-Type': 'application/ssml+xml', 'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm', 'User-Agent': 'demoreel'}))
    elif p == 'elevenlabs':
        key = need('ELEVENLABS_API_KEY')
        open(path, 'wb').write(http(f'https://api.elevenlabs.io/v1/text-to-speech/{voice}', json.dumps({'text': text, 'model_id': o.model or 'eleven_multilingual_v2'}).encode(),
            {'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'}))
    elif p == 'openai':
        key = need('OPENAI_API_KEY'); body = {'model': o.model or 'gpt-4o-mini-tts', 'voice': voice, 'input': text, 'response_format': 'wav'}
        if o.instructions: body['instructions'] = o.instructions
        open(path, 'wb').write(http('https://api.openai.com/v1/audio/speech', json.dumps(body).encode(),
            {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}))
    elif p == 'kokoro':
        global _KP
        try: from kokoro import KPipeline; import soundfile as sf
        except ImportError: sys.exit('ERROR: kokoro not installed → pip install kokoro "misaki[zh]" soundfile (a venv is recommended; see docs/voiceover.md)')
        lc = 'z' if zh else ('b' if o.lang.lower() == 'en-gb' else 'a')
        if '_KP' not in globals() or _KP[0] != lc: _KP = (lc, KPipeline(lang_code=lc, repo_id='hexgrad/Kokoro-82M'))
        audio = np.concatenate([np.asarray(a) for _, _, a in _KP[1](text, voice=voice, speed=o.speed)])
        sf.write(path, audio, 24000)
    elif p == 'say':
        if sys.platform == 'darwin': subprocess.run(['say', '-v', voice, '-r', str(int(180 * o.speed)), '-o', path, text], check=True)
        else: subprocess.run(['espeak-ng', '-v', 'zh' if zh else 'en-us', '-w', path, text], check=True)

def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)

def main():
    a = argparse.ArgumentParser(); a.add_argument('tsv'); a.add_argument('out')
    a.add_argument('--provider', required=True, choices=list(DEFAULT_VOICE)); a.add_argument('--voice'); a.add_argument('--lang', default='en')
    a.add_argument('--duration', type=float, default=30); a.add_argument('--model', help='polly engine / elevenlabs model_id / openai model')
    a.add_argument('--instructions', help='openai: delivery style, e.g. "friendly product demo, like a colleague showing you"')
    a.add_argument('--speed', type=float, default=1.0); a.add_argument('--lufs', type=float, default=-19); o = a.parse_args()
    clips = os.path.splitext(o.out)[0] + '_clips'; os.makedirs(clips, exist_ok=True)
    ext = {'polly': 'mp3', 'elevenlabs': 'mp3', 'say': 'aiff' if sys.platform == 'darwin' else 'wav'}.get(o.provider, 'wav')
    lines = [l.rstrip('\n').split('\t', 1) for l in open(o.tsv, encoding='utf-8') if '\t' in l and l.strip()]
    out = np.zeros(int(SR * o.duration)); man = []
    for i, (st, text) in enumerate(lines):
        st = float(st); path = os.path.join(clips, f'v{i:02d}.{ext}'); synth(o.provider, text, o, path)
        x = decode(path); d = len(x) / SR; man.append({'start': st, 'dur': round(d, 3), 'text': text, 'clip': os.path.abspath(path)})
        j = int(st * SR); k = min(len(out), j + len(x)); out[j:k] += x[:k - j]
        print(f'{i:2d} start={st:6.2f} dur={d:5.2f}  {text}')
    for k in range(len(man) - 1):
        e = man[k]['start'] + man[k]['dur']
        if e > man[k + 1]['start'] - 0.1: print(f'WARN: line {k} ends {e:.2f}s, next starts {man[k + 1]["start"]}s → shorten it (don\'t speed up the voice)')
    pk = np.abs(out).max()
    if pk > 0.98: out *= 0.98 / pk
    st = (np.repeat(out[:, None], 2, 1) * 32767).astype(np.int16)
    tmp = o.out + '.raw.wav'
    w = wave.open(tmp, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes()); w.close()
    # same loudness for every provider (−19 LUFS speech) → mix.sh's VO/music balance doesn't change when you switch engines
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', f'loudnorm=I={o.lufs}:TP=-2:LRA=11', '-ar', str(SR), '-t', str(o.duration), o.out], check=True); os.remove(tmp)
    json.dump(man, open(os.path.splitext(o.out)[0] + '.manifest.json', 'w'), ensure_ascii=False, indent=1)
    print(f'vo → {o.out}  (manifest {os.path.splitext(o.out)[0]}.manifest.json → align_subs.py for subtitles)')

if __name__ == '__main__':
    main()
