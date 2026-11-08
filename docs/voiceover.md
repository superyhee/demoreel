# Voice-over & subtitles setup

## Pick an engine — one command for all of them

```bash
python3 scripts/tts.py vo.tsv vo.wav --provider <P> --lang zh|en [--voice V] [--speed 1.0] --duration 30
python3 scripts/align_subs.py vo.manifest.json site/subs.json --lang zh --keywords "关键词,…"   # subtitles for ANY engine
```

| `--provider` | Quality | Chinese | Needs | Default voices (zh / en) |
|---|---|---|---|---|
| `azure` | ★★★★ | ★★★★★ | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` (free tier) | `zh-CN-XiaoxiaoNeural` / `en-US-AvaMultilingualNeural` |
| `elevenlabs` | ★★★★★ | good | `ELEVENLABS_API_KEY` | `21m00Tcm4TlvDq8ikWAM` (any voice id, `--model eleven_multilingual_v2`) |
| `openai` | ★★★★ | ok | `OPENAI_API_KEY` | `coral` (+ `--instructions "friendly product demo"`) |
| `minimax` | ★★★★★ (Chinese) | ★★★★★ | `MINIMAX_API_KEY` (+ `MINIMAX_API_HOST=api.minimax.io` for international keys; default `api.minimaxi.com`) | `female-chengshu-jingpin` / `English_Graceful_Lady` (300+ voices, `--model speech-02-hd`) |
| `polly` | ★★★ (generative ★★★★) | ok | AWS CLI credentials (below) | `Zhiyu` / `Ruth` (`--model neural|generative`) |
| `kokoro` | ★★★★ | yes | local, free, Apache-2.0 model — `pip install kokoro "misaki[zh]" soundfile` (≈330 MB download on first run) | `zf_xiaoxiao` / `af_heart` |
| `say` | ★★ | yes | macOS `say` / Linux `espeak-ng` — offline drafts | `Tingting` / `Samantha` |

- Keys are read **only from environment variables** (never from files in the project); `tts.py` never prints them.
  On macOS keep them in the keychain instead of shell history: `security add-generic-password -a demoreel -s MINIMAX_API_KEY -w` (prompts),
  then `export MINIMAX_API_KEY=$(security find-generic-password -a demoreel -s MINIMAX_API_KEY -w)`.
- Clips are trimmed to the voice (engines pad up to ~2 s of silence) and the track is loudness-normalised to **−19 LUFS**, so `mix.sh`'s voice/music balance doesn't change when you switch.
- `align_subs.py` (local faster-whisper, `pip install faster-whisper`, model downloads on first run) gives word timing for any
  engine — or for a **human VO recording**: `align_subs.py --tsv vo.tsv --audio vo.wav site/subs.json`. The screen always shows
  your script text; the recognizer only supplies timing. Measured against Polly speech marks: mean error **50 ms**, p90 130 ms.
- Kokoro/whisper pull PyTorch; a venv keeps it isolated: `python3 -m venv ~/.cache/demoreel-venv && ~/.cache/demoreel-venv/bin/pip install torch kokoro "misaki[zh]" soundfile faster-whisper`.
- Engine prices and model licences change — check the provider's pricing page / model card before publishing.

---

# Amazon Polly setup (`tts_polly.sh`, `subtitle_marks.py`, `tts.py --provider polly`)

DemoReel voices your film with **Amazon Polly** (`scripts/tts_polly.sh`) and times the dynamic subtitles with Polly
**speech marks** (`scripts/subtitle_marks.py`). No AWS account? Use the offline fallback (`scripts/tts_say.sh`) — see the end.

## 1. Install the AWS CLI

```bash
brew install awscli            # macOS   ·   Linux/Windows: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
aws --version
```

## 2. Give it credentials (least privilege)

Polly needs exactly one permission. Create an IAM user or role with **only** this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{ "Effect": "Allow", "Action": "polly:SynthesizeSpeech", "Resource": "*" }]
}
```

Then pick one way to sign in:

| Option | Command | When |
|---|---|---|
| IAM Identity Center (SSO) — recommended | `aws configure sso` → `export AWS_PROFILE=<profile>` | org / team accounts, short-lived credentials |
| Named profile | `aws configure --profile demoreel` → `export AWS_PROFILE=demoreel` | personal account |
| Environment variables | `export AWS_ACCESS_KEY_ID=… AWS_SECRET_ACCESS_KEY=…` | CI (use your CI's secret store) |

Never put keys in this repo, in `vo.tsv`, or in the HTML pages. Check what the scripts will use:

```bash
aws sts get-caller-identity
aws polly describe-voices --language-code en-US --query 'Voices[].[Id,SupportedEngines]' --output table   # optional, needs polly:DescribeVoices
```

## 3. Region

Both scripts use `POLLY_REGION`, else `AWS_REGION`, else **`us-east-1`** (it offers every engine).
Generative voices are only in some regions — if you get *"engine not supported"*, switch: `export POLLY_REGION=us-east-1`.

## 4. Voices & engines

| Language | Voice | Engine | Notes |
|---|---|---|---|
| English (US) | `Ruth` (f), `Matthew` (m) | `generative` (most natural) or `neural` | generative = no speech marks (see below) |
| Chinese (Mandarin) | `Zhiyu` (f) | `neural` | lang code `cmn-CN` |
| Japanese | `Kazuha` (f), `Takumi` (m) | `neural` | |
| Others | `aws polly describe-voices` | | |

```bash
S=scripts
$S/tts_polly.sh vo_en.tsv vo_en.wav Ruth neural en-US 30        # <start s><TAB><text> per line → one timed WAV
$S/tts_polly.sh vo_zh.tsv vo_zh.wav Zhiyu neural cmn-CN 30
python3 $S/subtitle_marks.py vo_en.tsv site/subs_en.json --voice Ruth --engine neural --lang en-US --max 30
python3 $S/subtitle_marks.py vo_zh.tsv site/subs_zh.json --voice Zhiyu --lang cmn-CN --keywords "关键词,另一个"
```

**Subtitles stay in sync only if both use the same voice + engine.** Polly returns speech marks for `standard`/`neural`, not
`generative` — `subtitle_marks.py` then falls back to neural timings, so render the VO with `neural` too (or accept small drift).

`tts_polly.sh` prints each line's duration and **WARNs when a line overruns the next start** → shorten the sentence, don't
speed up the voice.

## 5. Cost

A 30 s demo is ~300 characters; a 2-min film ~1,500. At Polly's per-million-character pricing (neural / generative) that is
**well under one US cent per render** — see the current [Polly pricing](https://aws.amazon.com/polly/pricing/) (new accounts
have a free tier). `synthesize-speech` creates no AWS resources, so there is nothing to clean up.

## 6. Troubleshooting

| Error | Fix |
|---|---|
| `ERROR: no AWS credentials` / `UnrecognizedClientException` | `aws configure` / `aws sso login`, or set `AWS_PROFILE` |
| `AccessDeniedException ... polly:SynthesizeSpeech` | attach the policy above to the user/role |
| `engine not supported` / `ValidationException` on voice | voice ↔ engine mismatch or region without that engine → `POLLY_REGION=us-east-1`, try `neural` |
| `TextLengthExceededException` | one TSV line is too long — split it (one idea per line anyway) |

## Offline / no AWS: `tts_say.sh`

```bash
scripts/tts_say.sh vo_zh.tsv vo_zh.wav Tingting 210 30    # macOS `say` voices (Tingting, Samantha, …); Linux: espeak-ng
```
Free and offline, but robotic — fine for drafts, not for publishing. Without Polly speech marks, write subtitles by hand
(`subtitles:{items:[{t0,t1,words:[{t,text}]}]}`) or skip them.
