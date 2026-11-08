# Voice-over & subtitles setup (Amazon Polly)

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
