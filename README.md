<div align="center">

# 🎬 DemoReel

### Turn any app into a launch-ready product demo video. One prompt, zero video editing.

**An AI-agent skill (Claude Code & friends) that directs, films, edits and voices software demos —<br>from a real screen recording *or* a pixel-perfect rebuilt UI — rendered frame-accurately, fully local.**

[![License: MIT](https://img.shields.io/badge/License-MIT-8b5cf6.svg)](LICENSE)
![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-skill-6366f1)
![Local first](https://img.shields.io/badge/render-100%25%20local-22c55e)
![Languages](https://img.shields.io/badge/VO%20%2B%20subtitles-any%20language-f59e0b)

<img src="assets/acme.gif" width="820" alt="DemoReel: 15 s demo of a fictional inbox app, generated from the starter template">

*15 s, generated from `templates/demo.html` — hook → logo → push-in → spotlight → callout → one CTA.*

</div>

---

## Why DemoReel?

Screen recordings look amateur. Motion-design tools take days. DemoReel gives your coding agent a **film crew**:

| You say | DemoReel does |
|---|---|
| *"Make a 30 s demo of our new inbox feature"* | explores the app, writes the storyboard, rebuilds the UI with fictional data (or records it for real), directs the camera, adds VO, subtitles, SFX and music, renders MP4 |
| *"Record our AI IDE actually doing the task"* | records the real session, **erases the tiny system cursor and draws a big smooth one**, speeds up the waiting with a live *"Agent working 08:26 · 12× timelapse"* clock, blurs private paths, boxes the key result |
| *"Now in English"* | same page, `?lang=en`, new VO + word-timed subtitles |

### What makes the output look *commercial*

- 🎥 **Camera that behaves like an editor** — optimal zoom/pan paths (van Wijk–Nuij), wide shots at 90 % with equal margins, close-ups that always fill the frame, automatic jitter detection.
- 🔦 **One focus at a time** — spotlight (light veil for white UIs, soft dim for dark UIs), animated callout boxes + labels, a declutter rule that never shows more than 3 overlay layers.
- 🖱️ **Screen-Studio-style cursor** — big, shadowed, tilting on motion, click squash + ripple; on real recordings the real pointer is tracked, erased and replaced.
- 💬 **Word-timed dynamic subtitles** — for any TTS engine or a human VO (local forced alignment, ~50 ms accuracy), current word highlighted, keywords accented.
- 🔊 **Sound that is half the film** — voice-over from Azure, ElevenLabs, OpenAI, Polly or local Kokoro, ducked under VO; procedural or library SFX (drop in Kenney CC0 packs, auto-ranked + auditioned); 5 music styles cued to the cut.
- ✅ **A commercial-quality gate** — `commercial_qa.py` checks 12 things a reviewer would reject (hook in 3 s, headline restraint, on-screen text ≥ 14 px, brightness, framing, clutter, one CTA, end-card shimmer…) *before* you render.

<div align="center">
<img src="assets/taskflow.gif" width="820" alt="Real screen recording of a fictional task app with spotlight, callout and cursor">

*Real footage mode: a scripted Playwright recording of a fictional app → camera, spotlight, callout, CTA.*
</div>

## Two ways to get footage (it always asks first)

| Mode | Best for | How |
|---|---|---|
| **Simulated UI** | launch films, unreleased features, any privacy concern, multi-language | rebuild the UI in HTML from screenshots, fictional data, every pixel editable |
| **Real recording** | dev tools & AI products where *"it really works"* matters | web (Playwright), desktop (macOS / Linux / Windows), iOS Simulator / Android, terminal (asciinema) |
| **Hybrid** | most commercial demos | real clips for the 1–3 moments that matter, rebuilt UI for the rest |

## Quick start

```bash
# 1. install as a Claude Code skill
git clone https://github.com/superyhee/demoreel ~/.claude/skills/demoreel

# 2. dependencies (macOS shown; Linux works too)
brew install ffmpeg
pip install playwright numpy pillow scipy opencv-python   # uses your installed Google Chrome (channel='chrome')
# optional: local voice + subtitle alignment →  pip install kokoro "misaki[zh]" soundfile faster-whisper

# 3. ask your agent
#    "用 demoreel 给我的 app 做一个 30 秒的产品演示视频"  /  "Make a 30-second product demo of my app"
```

**Voice-over (optional):** one command for **Azure, ElevenLabs, OpenAI, Amazon Polly, Kokoro (free, local) or `say`** —
`scripts/tts.py vo.tsv vo.wav --provider kokoro --lang en`, then `scripts/align_subs.py` gives word-timed subtitles for any engine
(even a human recording). Keys via env vars only. Setup & voices: **[docs/voiceover.md](docs/voiceover.md)**.

Or drive it by hand:

```bash
S=~/.claude/skills/demoreel/scripts
cp ~/.claude/skills/demoreel/templates/{demo.html,engine.js,logo_t.png} site/
python3 $S/commercial_qa.py site/demo.html             # fix every FAIL
python3 $S/render_parallel.py site/demo.html out.mp4   # 6 Chrome workers, ~25–30 fps
$S/tts_polly.sh vo.tsv vo.wav Ruth neural en-US 15     # or tts_say.sh (offline)
python3 $S/subtitle_marks.py vo.tsv site/subs.json --voice Ruth --lang en-US
MUSIC_GAIN=0.2 $S/mix.sh out.mp4 vo.wav music.wav sfx.wav final.mp4 30 15
```

## How it works

```
explore app ─► storyboard ─► HTML page (simulated UI or footage layer)
                                  │  engine.js: camera · spotlight · cursor · captions · subtitles · callouts · clock
                                  ▼
            shot_qa / camera_qa / commercial_qa  (seconds, before rendering)
                                  ▼
       render_parallel.py  (pure render(t) → frame-accurate, N Chrome workers → ffmpeg)
                                  ▼
          TTS + SFX + music  ─►  mix.sh (look-ahead ducking, −16 LUFS)  ─►  MP4 + SRT
```

Everything is a pure function of time `t`, so any frame range renders independently and identically — no screen capture of a live animation, no dropped frames.

## What's inside

| Path | What |
|---|---|
| `SKILL.md` | the agent playbook (phases, checkpoints, quality bar) |
| `templates/` | `engine.js`, a simulated-UI starter, a real-footage starter |
| `scripts/` | recording (web/desktop/mobile/terminal), cursor tracking & erase, text redaction, footage editing, rendering, QA, TTS, subtitles, SFX, music, mixing |
| `references/` | engine API, benchmark checklist, pitfalls learned the hard way, audio QA |
| `examples/` | a fictional web app + recording steps for the real-footage path |

## Honest limitations

- Synthesized music is fine for drafts and internal demos — **use licensed music for public launches**.
- Linux / Windows / Android recorders are implemented but less battle-tested than macOS + web.
- The agent can't *watch* the film: QA is numeric (framing, flicker, loudness, clutter…) — always have a human look at it on a phone.

## 中文简介

**DemoReel：一句话，把任何软件变成可直接发布的产品演示视频。**
给 AI 编程助手（Claude Code 等）的"摄制组" skill：自动探索应用 → 写分镜 → 真实录屏或像素级重建界面 → 运镜、聚光灯、标注、大光标 → 配音（Polly）、逐词动态字幕、音效、配乐 → 本地逐帧渲染 MP4。内置 12 项商业化质量检查（开场钩子、文字大小、亮度、取景、杂乱度、单一 CTA、片尾文字抖动……），渲染前就能发现问题。支持中英等任意语言。

## Contributing

Issues and PRs welcome — start with a [**good first issue**](https://github.com/superyhee/demoreel/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) (Windows/Linux recording tests, terminal & mobile templates, a before/after showcase). Especially wanted: recorders tested on Linux/Windows/Android, new templates (mobile, terminal, dashboard), multi-aspect (9:16 / 1:1) reframing, and real-world before/after demos.

If DemoReel saved you a week of video editing, a ⭐ helps others find it.

## Security

Recording tools capture whatever is on screen — use a demo account, and see [SECURITY.md](SECURITY.md) for safe-recording tips and private vulnerability reporting.

## License

[MIT](LICENSE). Bring your own sound libraries (e.g. Kenney packs are CC0) and keep their license files. Product names in your own demos belong to their owners.
