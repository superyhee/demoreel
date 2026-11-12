---
name: demoreel
description: Produce a polished 15 s–3 min product/feature demo video for ANY software (desktop app, web app, SaaS, CLI) entirely locally. ALWAYS starts by asking the user which footage mode to use — REAL screen recording of the app, SIMULATED UI rebuilt in HTML with fictional data, or HYBRID. Explores the real app (computer use / browser), records real sessions or rebuilds the UI, animate with a camera/cursor/caption engine, render frame-accurately with Chrome, add Polly (or macOS say) voiceover, SFX and music, and encode MP4 in multiple languages. Use when the user asks for 产品 demo 视频, 功能演示视频, 宣传短片, feature walkthrough video, product demo, promo video for a software feature — especially when ChatCut/Fabric video MCPs are unavailable or when a crisp, editable, multi-language result is wanted.
---

# Software Demo Video (local HTML → MP4 pipeline)

Battle-tested on: a 30 s SaaS feature film (zh + en), a 2-min AI-IDE launch film (simulated UI) and a real 13-min AI-agent session (screen recording).
Toolchain: Chrome + Python Playwright (`channel='chrome'`), ffmpeg, numpy/PIL, `cliclick`, AWS CLI (Polly).
All paths below are relative to this skill dir: `~/.claude/skills/demoreel/`.

## Checkpoints (one per reply, wait for the user)
0. **Footage mode (MANDATORY, ask before any exploring/recording)** — real recording vs simulated UI vs hybrid; see "Phase 0".
1. **Feature understanding + privacy** — after exploring the app, list what the feature does; flag any real data visible.
2. **Script + storyboard** — table `| # | 时间 | 画面 | 文案/配音 |`; confirm aspect/language/voice AND the opening: offer 2–3 hooks
   from `references/hooks.md` that fit this feature (ASCII previews), different from the last film of the same product.
3. **Result** — deliver MP4 path(s), what was verified, honest score + what's still missing.
Skip waiting only if the user explicitly says to run end-to-end.

## Phase 0 — Choose the footage mode (ask with AskUserQuestion BEFORE doing anything else)
Ask exactly this decision (one question, three options, recommendation first based on the situation), then record the
answer in the project notes. Never start computer-use clicking or screen recording before the user picked a mode.

| Mode | What it is | Pick when | Costs / risks to state in the question |
|---|---|---|---|
| **模拟界面 SIMULATED** | Rebuild the app UI in HTML from screenshots, fictional data, animate with engine.js | marketing/launch films, any real-data/privacy concern, features not built yet, multi-language, perfect pacing, unattended rendering | ~1–2 h UI build; must match real UI faithfully; viewers may ask "is it real?" |
| **真实录制 REAL** | Record the real app (record_web.py for web apps, record_mac.sh / computer use for desktop) → footage layer + camera/spotlight/captions | dev tools & AI products where credibility matters, tutorials, sales/POC demos, "show it actually works" | needs a DEMO account/project (no real data); the app's AI really runs (credits, minutes of waiting); **desktop recording captures whatever is frontmost** → the user must not use the machine for the session (~20–40 min), or use a dedicated Space/display; approvals inside the app |
| **混合 HYBRID** (often best) | Real footage for 1–3 core moments + simulated UI for the rest (hooks, unbuilt/slow/private parts, outcome cards) | most commercial demos | both of the above, scoped down |

Confirm the exact feature in the same question (a mid-task switch to another feature is the costliest restart). Questions to include with the mode choice when relevant: demo account/project available? OK to spend app credits? can the
machine be left alone for the recording window? Then route: SIMULATED → Phases 1–5; REAL → Phase 1 (explore) + "Real
footage path"; HYBRID → both, decide per storyboard row (add a column `素材: 真实/模拟`).


## Software coverage matrix
Which recorder / rebuild path per software type (web, macOS / Linux / Windows desktop, Electron/IDE, iOS, Android, CLI): `references/real-footage.md`.

## Phase 1 — Explore the real software
- **Desktop app** (Electron/native), one step per call: `scripts/explore_act.sh "<App>" - shots/s0 none` → Read
  `shots/s0_small.png`; then `explore_act.sh "<App>" - shots/s1 click X,Y` (`scroll X,Y,N,up|down`, `key kp:esc`) with X,Y read
  off the PREVIOUS `_small.png` — the script converts them using the window's current position. It screenshots ONLY the app's
  window (`screencapture -l`, works even when the app is behind others), so the user's other apps (chat, mail) never land in a
  shot; it re-activates the app and verifies it is frontmost right before every click (terminals / chat apps steal focus —
  the #1 time sink and a privacy risk), and aborts without clicking otherwise. Nested chat/feed panes need the wheel
  (`scroll`), not Home/End keys. Avoid full-screen `shot.sh` once the user's machine is in use. Before exploring, ask the
  user to leave the machine alone for ~5 min (or send screenshots instead). Restore UI state you changed.
- **Web app**: chrome-devtools / playwright MCP (`take_snapshot`, `click`, `take_screenshot`).
- Capture: every tab/state of the feature, item anatomy (tags, actions, sources), empty states, brand colors, fonts, logo.
- A term like「信息流」may be a **feature name inside the app**, not an ad format — verify in the UI before assuming.
- **Logo**: take the REAL one, never redraw, never ship `templates/logo_t.png` (placeholder for a fictional product):
  installed app → `scripts/app_logo.py "/Applications/<App>.app" site/` (app_icon.png for hero/end card, logo_glyph.png for the
  in-UI mark); otherwise crop a screenshot: `scripts/logo_alpha.py shot.png x y w h site/logo.png` (full-res px). Do this in
  Phase 1, before the first preview. Note the product name exactly as the current UI shows it (brands get renamed).

## Phase 2 — Privacy decision (always ask)
Real workspaces contain colleague/customer names, IPs, project details. Default recommendation:
**rebuild the UI in HTML from screenshots, with fictional data** (crisp text, no leak, fully editable, any language).
Alternatives: record real screen + blur (most content ends up blurred), or internal-only raw capture.

## Phase 3 — Script
- Before writing, run the 8-point checklist in `references/benchmarks.md` (hook, one storyline, real footage, spotlight, visible results, sound, restraint, one CTA).
- Narrative that works: **Hook (0–3s, type chosen from `references/hooks.md` — not always the chaos/pain card) → Logo/name
  (3–5s, or only on the end card) → 5–6 feature beats of 3–4s each → End card (last 3–4s)**. Record the chosen opening in
  the project's `demo_notes.md` (`hook: result-first`) so the next film of the same product opens differently.
- One idea per beat; captions = outcome, not feature list. ~1 visual change every 2–3s.
- Copy budget (30s): zh ≈ 9 short lines (≤12 字), en ≤ 7 words per line. Feed videos are often muted → captions carry the story.
- Write VO as `vo_<lang>.tsv` (`start<TAB>text`). Start each line ~0.1–0.3s after its beat begins.

## Commercial defaults (engine, no config needed)
spotlight dim 0.35 / blur 1.2 (capped 0.4 / 1.6) · headline cards ≤ 3.2 s (flag hooks/full-screen cards with 4th elem 'hold') ·
camBounds '#win' framing (wide 90 % / close-up fill) · subtitles from `subs.js` (subtitle_marks.py) · declutter ≤ 3 overlay layers ·
cursor shadow/tilt/squash · no minimap. Opt out per key (e.g. `captionMax:0`, `declutter:false`). Templates already wire notes/clock/CTA.

## Phase 4 — Build the animation page
`cp templates/demo.html templates/engine.js <proj>/site/` (+ `logo_t.png`). Read `references/engine.md` for the API.
- Put **all visible strings in the `L={zh:{},en:{}}` table**; `?lang=en` switches language (one page, many languages).
- Rebuild the real layout (sidebar, tabs, cards, tags, buttons) from screenshots; use `H.I('icon')` Lucide-style SVG icons — **no emoji** (looks fake).
- Timeline = `Demo.init({cam, camIn, camOut, cursor, clicks, captions, sfx, scene, post})`.
  Camera keyframes target selectors; the engine auto-fits them into the safe area, so layout changes (expanding rows) are followed automatically.
- `scene(t)` must be a pure function of `t` (no Date/requestAnimationFrame/CSS transitions) → deterministic frames.
- **Animate with the behaviour helpers, don't hand-roll them** (`references/engine.md`): `H.reveal` / `H.popover` (layout
  stays → camera targets keep their size), `H.stream` (AI output, typing), `H.step` (agent/job traces), `H.scrollAnchor`
  (chat / feed / doc panes; pad ≈ 64 px keeps anchors below the headline pill). They are UI-agnostic — the layout and look
  must still come from the real app's screenshots; never start from another product's page. Run `shot_qa.py` right after
  the first draft — it catches framing problems in seconds.

## Phase 5 — Preview → iterate (cheap) → render (expensive)
```bash
S=~/.claude/skills/demoreel/scripts
python3 $S/preview_sheet.py site/index.html shots/sheet.png --lang zh 1.8 4.2 7.2 11.5 15.8 19.6 22.4 25.5 28.5
```
Read the sheet; also crop a zoomed frame at full res to check text sharpness. Fix, re-preview.
**Visual review (taste gate, before rendering):** `python3 $S/visual_review.py site/index.html review/ --lang zh` picks the frames a
reviewer looks at (hook, each hold, mid-move, callouts, headlines, end card) → Read `review/sheet_*.png`, score `review/rubric.md`
(10 criteria 0/1/2: hook, focus, legibility, framing, collisions, polish, story, restraint, end card, trust) with frame ids + one fix
each; apply the top 3 fixes, re-run. Numeric QA can't see collisions, empty establishing shots or half-drawn states — this does.
`--api` sends the same frames + rubric to Claude (claude-opus-5-5, server-side refusal fallback; `--provider bedrock --region …`) and
writes review.md/json — costs API credits, ask first; `--dry-run` shows the payload size; `--mp4 out.mp4` reviews the encoded film.
Calibrated on the starter template: it catches what numeric QA can't (a hard spotlight blur edge cutting a button, a duplicated
callout, the cursor covering a label), but totals drift between runs (same 14/20 with different findings) → act on the cited
frames/evidence and gate only on 0 scores (exit 1), never on the total. Bedrock: `claude-opus-5-5` may only be served in some
regions (us-east-1 worked; us-west-2 returned 404).
**Other aspects (social cuts):** the same page renders 9:16 / 1:1 / 4:5 with `--aspect` on every script (`render_parallel.py …
--aspect 9:16`, `commercial_qa.py --aspect 9:16`, `final_check.py --aspect 9:16`, `preview_sheet.py`, `visual_review.py`). Close-ups
switch to the 'fit' rule (target fills the width, ≥1.3×); re-lay out hook / logo / end card with `body.ar-9x16 …` CSS (see
templates/demo.html) and, if a shot doesn't work vertically, override it: `aspects:{'9:16':{cam:[…]}}`. Run QA per aspect. Then:
```bash
python3 $S/render_parallel.py site/index.html video_zh.mp4 --lang zh   # DEFAULT: 6 Chrome workers → ~37 fps (120 s video ≈ 96 s), no PNGs
python3 $S/render_parallel.py site/index.html video_zh.mp4 --frames-dir frames_zh   # also keep PNGs (flicker_check)
python3 $S/render_frames.py site/index.html frames_zh --lang zh      # single-process fallback (~9 fps)
python3 $S/render_frames.py site/index.html frames_zh --lang zh --from 700 --to 730   # re-render only a fixed range
```


## Real footage path (REAL / HYBRID — preferred for dev tools / AI products)
Read `references/real-footage.md` before recording: demo account only, `record_web.py` / `record_desktop.sh` / `record_mobile.sh` /
`record_terminal.sh` → `footage_edit.py` → `footage_prep.py` → verify hotspots with `hotspot_overlay.py` → `templates/footage-demo.html`.
Desktop recording: guard EVERY click with `guarded_act.sh`, filter foreign windows with `footage_mask.py`, and if the user's private
windows appear STOP the recording and tell them. Cursor enhancement, typing, privacy redaction and commercial polish are in the same file.

## Phase 6 — Audio
Read `references/audio.md` (all engines, commands, music styles, Kenney SFX, beat grid, subtitles). The essentials:
- ONE venv with both requirement files: `PY=~/.cache/demoreel-venv/bin/python` (`pip install -r requirements.txt -r requirements-voice.txt`).
- Start VO + subtitle alignment as ONE background job right after the script is approved, while you build the page; languages sequentially.
```bash
$PY $S/tts.py vo_zh.tsv vo_zh.wav --lang zh --duration 30          # default Polly; --provider kokoro|minimax|azure|elevenlabs|openai|say
$PY $S/align_subs.py vo_zh.manifest.json site/subs_zh.json --lang zh --keywords "…"
python3 $S/sfx.py sfx_zh.json sfx_zh.wav 30                          # sfx json is written by the renderer
python3 $S/music_pro.py music.wav --dur 30 --hit 3.55 --groove 5 --main 9 --lift 21 --peak 23 --drop 26 --end 26.6
python3 $S/beat_grid.py site/beats.js --bpm 120 --start 5 --dur 30   # or --wav licensed.wav → cuts land on the beat
$PY $S/audio_qa.py music.wav vo.wav --gain 0.2
```
- A line overruns the next start → **shorten the sentence** (never speed the voice). Check `aws sts get-caller-identity` before Polly.
- Ask the user for licensed music for anything published; synthesized music is the #1 thing that reads as amateur.

## Phase 7 — Mix, encode, verify
```bash
MUSIC_GAIN=0.2 $S/mix.sh video_zh.mp4 vo_zh.wav music.wav sfx_zh.wav ~/Downloads/<Name>_zh.mp4 30 30   # 0.2 for music_styles/music_pro (-12 LUFS), 0.42 for music.py/licensed (~-18 LUFS)
```
mix.sh: VO +4 dB; music gets a -4 dB dip at 2.5 kHz and **lookahead ducking** (sidechain = VO advanced 150 ms, ratio 10) so
first syllables aren't masked; SFX room-verbed + stereo; master loudnorm -16 LUFS / -1.5 dBTP.
Audio QA (numbers, since you can't listen): see `references/audio-qa.md` — speech-band SNR p5 ≥ 10 dB, sub share 30–40%, section energy rising into the peak.
**Commercial gate (MANDATORY, any software, both modes): `python3 $S/commercial_qa.py site/index.html` → fix every FAIL before rendering**
(hook, length, subtitles, headline restraint, spotlight, framing, ≤3 overlay layers, on-screen text ≥14 px, brightness, ONE CTA,
cursor off end card, callouts, no placeholder logo, end-card product name present in the VO). Report its score + the MANUAL items (music licence, VO, facts/brand review, phone viewers) to the user.
Final deliverable (each MP4): `python3 $S/final_check.py out.mp4 --page site/index.html --lang zh` → streams, duration, −16 LUFS,
true peak ≤ −1 dBTP, black frames, and a contact sheet of the TRANSITION frames → Read it. align_subs/subtitle_marks also
write `subs_<lang>.srt` next to the json — ship it with the MP4. Verify before reporting: `python3 $S/shot_qa.py site/index.html` (0 framing issues) and `python3 $S/camera_qa.py site/index.html` (0 direction reversals = no jitter) — both run BEFORE rendering, in seconds; `python3 $S/flicker_check.py frames_zh` (0 spikes), extract frames at transitions (`ffmpeg -ss T -i out.mp4 -frames:v 1 x.png`) and Read them;
`max_volume` should be ≤ -1 dB. Say plainly what was and wasn't checked (e.g. "didn't watch/listen end-to-end").
Keep previous versions (suffix `_v2`) rather than overwriting unless asked to replace.

## Quality bar
What separates a 6.5 from an 8.5 film (problem → fix table): `references/quality-bar.md`. Remaining gap to 9+: licensed music,
1–2 real recorded clips from a demo account.

Pitfalls: see `references/pitfalls.md` (3D blur, zsh word-splitting, Playwright browser, Polly timing…).
