# Security Policy

## Reporting a vulnerability
Please **do not open a public issue**. Use GitHub's private reporting:
**Security → Report a vulnerability** on this repository. You'll get a reply within a few days.

## Scope
DemoReel runs locally: it renders HTML pages in your own Chrome, records your screen/devices and calls the TTS provider you
configure. It starts no network listeners and ships no credentials.

## Using DemoReel safely
- **Screen recording captures whatever is on top.** Record a demo account / demo project in its own window, never real customer data.
  `scripts/footage_mask.py` drops frames where another window took focus; `scripts/redact_text.py` blurs private words (user names,
  paths, emails) in every frame — re-scan after redacting.
- **Never commit recordings, frames or audio** of real sessions (`.gitignore` excludes `frames*/`, `rec/`, `*.mp4`, `*.wav`).
- Cloud TTS (`tts_polly.sh`, `subtitle_marks.py`) uses your local AWS CLI credentials; nothing is stored in this repo.
- Treat downloaded sound/asset packs as untrusted data: unzip only media + license files into their own folder.
