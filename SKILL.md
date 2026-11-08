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
2. **Script + storyboard** — table `| # | 时间 | 画面 | 文案/配音 |`; confirm aspect/language/voice.
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

Questions to include with the mode choice when relevant: demo account/project available? OK to spend app credits? can the
machine be left alone for the recording window? Then route: SIMULATED → Phases 1–5; REAL → Phase 1 (explore) + "Real
footage path"; HYBRID → both, decide per storyboard row (add a column `素材: 真实/模拟`).


## Software coverage matrix (pick per product; HYBRID mixes rows)
| Software type | REAL recording | SIMULATED UI | Notes |
|---|---|---|---|
| Web app / SaaS | `record_web.py` (scripted Playwright, no desktop capture, repeatable, step-time log) | rebuild from screenshots (`templates/demo.html`) | best case for REAL; needs demo account / logged-in profile |
| Desktop app — macOS | `record_desktop.sh --window "<App>" "<title>"` + `guarded_act.sh` + `footage_mask.py` | rebuild | user must leave the machine alone; crop the Dock |
| Desktop app — Linux | `record_desktop.sh` (x11grab / wf-recorder on Wayland), `shot.sh` (import/scrot/grim), clicks via xdotool/ydotool | rebuild | untested on a real Linux box yet — dry-run first |
| Desktop app — Windows | `record_desktop.sh` (gdigrab, window by title) from Git-Bash; clicks via AutoHotkey/pywinauto | rebuild | untested yet — dry-run first |
| Electron / IDE (VS Code, Cursor, …) | as desktop; open a demo folder in its OWN window | rebuild (templates/demo.html) | the app's AI really runs → credits + minutes of waiting → speed-ramp |
| Mobile — iOS | `record_mobile.sh ios` (Simulator) ; physical device via QuickTime | rebuild inside a phone frame | put footage in a phone bezel (footage template `FRAME='phone'`) |
| Mobile — Android | `record_mobile.sh android` (adb screenrecord ≤180 s / scrcpy) | rebuild inside a phone frame | |
| CLI / terminal | `record_terminal.sh` (asciinema → agg, real output, crisp text, theme/font control) | engine terminal panel (rebuilt in HTML) | script the commands; add typing pauses |
| Not-yet-built feature / private data / risky actions | — | SIMULATED only | never record real customer data |
Long recordings → `footage_edit.py` (cut + speed + crossfades) → `footage_prep.py` (de-flash, step-dissolve) → footage layer.

## Phase 1 — Explore the real software
- **Desktop app** (Electron/native): `scripts/shot.sh /tmp/<proj>/shots/s0 "<App Name>"` → Read the `_small.png`;
  click with `cliclick c:X,Y` using logical coords (`small_x * logical_width/1600`; logical width = pixel width/2 on retina,
  check with `sips -g pixelWidth`). Screenshot after every click. Restore UI state you changed (collapse what you expanded).
- **Web app**: chrome-devtools / playwright MCP (`take_snapshot`, `click`, `take_screenshot`).
- Capture: every tab/state of the feature, item anatomy (tags, actions, sources), empty states, brand colors, fonts, logo.
- A term like「信息流」may be a **feature name inside the app**, not an ad format — verify in the UI before assuming.
- **Logo**: crop the real one from a screenshot: `scripts/logo_alpha.py shot.png x y w h site/logo_t.png` (full-res px). Never redraw.

## Phase 2 — Privacy decision (always ask)
Real workspaces contain colleague/customer names, IPs, project details. Default recommendation:
**rebuild the UI in HTML from screenshots, with fictional data** (crisp text, no leak, fully editable, any language).
Alternatives: record real screen + blur (most content ends up blurred), or internal-only raw capture.

## Phase 3 — Script
- Before writing, run the 8-point checklist in `references/benchmarks.md` (hook, one storyline, real footage, spotlight, visible results, sound, restraint, one CTA).
- Narrative that works: **Hook pain (0–3s) → Logo/name (3–5s) → 5–6 feature beats of 3–4s each → End card (last 3–4s)**.
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

## Phase 5 — Preview → iterate (cheap) → render (expensive)
```bash
S=~/.claude/skills/demoreel/scripts
python3 $S/preview_sheet.py site/index.html shots/sheet.png --lang zh 1.8 4.2 7.2 11.5 15.8 19.6 22.4 25.5 28.5
```
Read the sheet; also crop a zoomed frame at full res to check text sharpness. Fix, re-preview. Then:
```bash
python3 $S/render_parallel.py site/index.html video_zh.mp4 --lang zh   # DEFAULT: 6 Chrome workers → ~37 fps (120 s video ≈ 96 s), no PNGs
python3 $S/render_parallel.py site/index.html video_zh.mp4 --frames-dir frames_zh   # also keep PNGs (flicker_check)
python3 $S/render_frames.py site/index.html frames_zh --lang zh      # single-process fallback (~9 fps)
python3 $S/render_frames.py site/index.html frames_zh --lang zh --from 700 --to 730   # re-render only a fixed range
```


## Real footage path (preferred for dev tools / AI products — credibility)
1. Record with a DEMO account (never real customer data):
   - web app: `python3 $S/record_web.py <url|file.html> rec.mp4 --steps steps.json` (scripted, repeatable; writes rec_events.json with step times)
   - desktop app: `$S/record_desktop.sh rec.mp4 SECONDS --window "<App>" "<title>"` (macOS/Linux/Windows; needs Screen Recording permission on macOS)
   - mobile: `$S/record_mobile.sh ios|android rec.mp4 SECONDS` · terminal/CLI: `$S/record_terminal.sh rec.mp4 commands.sh`
   - long session → `$S/footage_edit.py rec.mp4 segments.json edit.mp4 --crop W:H:0:0 --start <t>` (speeds, crossfades at jumps, timing json)
2. `python3 $S/footage_prep.py edit.mp4 rec/ --fps 30` → image sequence (+ de-flash single-frame repaints, 6-frame dissolve on hard brightness steps) + config snippet.
3. Measure hotspots ON the prepped footage, then VERIFY: `python3 $S/hotspot_overlay.py rec/ hot.json overlay.png --frames 1,500` — every box must match its panel with equal left/right margins (snap to the printed UI edges). Never convert screenshot coords by hand without this check.
4. `cp templates/footage-demo.html` → fill FOOT, MAP (project→footage seconds: slope>1 = speed-up with "⏩ ×N" badge, flat = freeze), HOT (hotspots in footage px = camera/spot/cursor targets), SHOTS/SPOTS/CUR.
5. preview_sheet → render_parallel → mix.sh, exactly as for rebuilt UIs. Worked example: examples/footage-taskflow/ (app + steps) → ~/Downloads/TaskFlow_真实录屏样片_16s.mp4.
Desktop computer-use recording (learned on a real AI-IDE session):
- Make a fictional demo project; open it in its OWN window; position it (`osascript … set position/size`); record only that region.
- Guard EVERY click: `scripts/guarded_act.sh "<App>" "<window-title-substring>" <label> <cliclick args>` refuses to click unless that app+window is frontmost, and logs the recording-relative time (needed for the time map).
- Other apps WILL come to front (terminal agents, Teams, the same app's other windows) → after recording run `scripts/footage_mask.py rec.mp4 --title-ref <t> --title-box x,y,w,h` to keep only frames whose title bar matches the demo window. Never trust an activity-bar check: two windows of the same app look identical there.
- Crop the Dock (it overlaps the window bottom), cap each recording (≤20 min) and restart, approve in-app shell commands one at a time ("Allow", never "Always allow") after reading them.
- If the user's private windows appear, STOP the recording immediately and tell them; offer to delete or filter that file.
Cursor enhancement (Screen-Studio style, real recordings): `cursor_track.py cut` (1 sample per pointer kind; cut a separate
light-background I-beam `ibeamL`, give thin templates `thr≈0.04` in tpl.json) → `track` (rec_orig/) → `erase site/rec --backup rec_orig`
(temporal patch, inpaint fallback) → `cursorTrack:{data, size:46, clicks:[logged t…]}` in Demo.init. The engine keeps rests exact,
turns every move into one eased glide that ends on arrival, snaps clicks to arrival (ripple + press + click SFX), hides while typing.
Typing (hybrid): freeze the footage on the frame where the text is complete and reveal it with `typing:[{t0,t1,lines,bg}]` (real
glyph pixels, uneven cadence, soft ticks). If the pointer rested on that text, repair glyphs by re-rendering the text in the UI font
inside the erased area only (examples/glyph_fix_example.py; see pitfalls.md).
Privacy redaction: `redact_text.py rec/ --tpl f01960.jpg:x,y,w,h …` (one crop of the private word per font/size/background) blurs
every occurrence in all frames; re-scan with a lower threshold to confirm 0 misses. Better: record from a path without the user
name (e.g. /Users/Shared/<demo>) and a neutral macOS account.
Commercial polish — works for BOTH modes: `notes:[{t0,t1,sel|box,label,side}]` animated highlight box + label (sel = page elements
in simulated UIs, box = footage px); `clock:{segs,zero,stopAt,label,done,show}` work clock for simulated agent runs (top level) or
`footage[i].clock` for recordings; `subtitles` (subtitle_marks.py); headline captions ≤3.2 s; unified cursor look (shadow, tilt, squash).
Real footage:
`footage[i].clock:{segs,zero,stopAt}` replaces "⏩×N" with a running real-time work clock ("Agent 工作中 08:26 · 12× 延时" →
"✓ 完成 13:07"); headline captions ≤3.2 s per beat; excerpt cards with REAL text from the produced artifact (never invented)
when the footage didn't scroll to it; end card = 3–4 outcome numbers counted up + ONE CTA. Hide the cursor on intro/end cards.
Notes: headless recordings have NO mouse pointer → add the engine cursor on hotspots at the click times (convert recording times with the MAP). Light UIs need softer spotlight (`dim≈0.3, fadeIn 1.0, fadeOut 0.8`). Mix both paths freely: real footage for the core flow, rebuilt UI for things you can't record.

## Phase 6 — Audio
Any TTS engine (azure / elevenlabs / openai / polly / kokoro local / say) + subtitles for any engine or a human VO — docs/voiceover.md:
```bash
python3 $S/tts.py vo_zh.tsv vo_zh.wav --provider kokoro --lang zh --duration 30          # → vo_zh.wav + vo_zh.manifest.json (−19 LUFS)
python3 $S/align_subs.py vo_zh.manifest.json site/subs_zh.json --lang zh --keywords "…"   # faster-whisper word timing, script text kept
# classic Polly-only path:
$S/tts_polly.sh vo_zh.tsv vo_zh.wav Zhiyu neural cmn-CN 30       # zh (neural)
$S/tts_polly.sh vo_en.tsv vo_en.wav Ruth generative "" 30         # en (generative; Matthew = male)
$S/tts_say.sh   vo_zh.tsv vo_zh.wav Tingting 210 30               # offline fallback (robotic)
python3 $S/sfx.py sfx_zh.json sfx_zh.wav 30                       # sfx json is written by render_frames.py
python3 $S/music_pro.py music.wav --dur 30 --hit 3.55 --groove 5 --main 9 --lift 21 --peak 23 --drop 26 --end 26.6
# ^ procedural score arranged to the cut: tension ticks+riser → logo impact → light groove → full groove
#   (sidechain pump) → riser lift → peak w/ bell lead → drop → end chord hit + tail. Mastered loud (~-11 LUFS).
python3 $S/music.py music.wav 30 120 5.0 26 3.6                   # older minimal placeholder
python3 $S/music_styles.py styles/ --all  [same cue args]            # 5 styles, all -12 LUFS: electronic piano lofi cinematic minimal
python3 $S/music_styles.py music.wav --style piano [cue args]       # one style
python3 $S/audio_qa.py music.wav vo.wav --gain 0.2                  # arc / sub share / speech-band SNR (p5 >= 10 dB)
```
- **Real UI sounds (recommended over synthesis for click/tick/pop/chime)**: Kenney CC0 packs (kenney.nl: Interface Sounds, UI Audio,
  Impact Sounds, Digital Audio, Music Jingles — commercial use, no attribution; keep License.txt). Put them in ~/Downloads/kenney/,
  `python3 $S/sfx_lib.py index ~/Downloads/kenney lib.json` → `sfx_lib.py audition lib.json 试听/` (let the user pick by ear) →
  `sfx.py sfx.json sfx.wav DUR --lib lib.json` (level-matched to the synthesized gains, rotated per event; empty pick = synthesized).
  Default: library click/tick/pop/chime; keep synthesized boom/whoosh/suck/shimmer (library impacts are thin, maximize sweeps sound
  game-like). Avoid laser/powerUp/zap/phaser/error sounds in product demos. Kenney has NO background music beds (jingles only).
- Offer the user a choice: mix one preview per style into a folder and let them pick by ear.
- Map cue points from the video timeline: `hit`=logo, `groove`=UI appears, `main`=first feature beat, `peak`=last 1–2 beats, `end`=end card.
- Licensed music still beats it for public launches; music_pro is good enough for internal/demo-day/social drafts.
- Check AWS identity first (`aws sts get-caller-identity`); Polly synthesize-speech creates no resources, cost ≈ cents.
  Setup for new users (CLI, least-privilege IAM policy, region via POLLY_REGION, voices, troubleshooting): `docs/voiceover.md`.
- If tts warns a line overruns the next start → **shorten the sentence** (don't speed the voice).
- Ask the user for licensed music for anything published; synthesized music is the #1 thing that reads as amateur.

Dynamic subtitles (VO-synced, word-by-word highlight, keyword accent) — after the VO tsv is final:
```bash
python3 $S/subtitle_marks.py vo_zh.tsv subs.json --voice Zhiyu --lang cmn-CN   # Polly speech marks → phrases + word times
```
Paste into the page: `subtitles:{items:SUBS, keywords:['Spec',…], accent:'#b98bff', size:40}` in Demo.init. Default position is
fixed at the bottom (user preference); `position:'auto'` moves them under the caption band when the focus target is at the bottom.
Speed badge sits bottom-left so it never collides with subtitles. Also ship the .srt for platforms with native captions.

## Phase 7 — Mix, encode, verify
```bash
MUSIC_GAIN=0.2 $S/mix.sh video_zh.mp4 vo_zh.wav music.wav sfx_zh.wav ~/Downloads/<Name>_zh.mp4 30 30   # 0.2 for music_styles/music_pro (-12 LUFS), 0.42 for music.py/licensed (~-18 LUFS)
```
mix.sh: VO +4 dB; music gets a -4 dB dip at 2.5 kHz and **lookahead ducking** (sidechain = VO advanced 150 ms, ratio 10) so
first syllables aren't masked; SFX room-verbed + stereo; master loudnorm -16 LUFS / -1.5 dBTP.
Audio QA (numbers, since you can't listen): see `references/audio-qa.md` — speech-band SNR p5 ≥ 10 dB, sub share 30–40%, section energy rising into the peak.
**Commercial gate (MANDATORY, any software, both modes): `python3 $S/commercial_qa.py site/index.html` → fix every FAIL before rendering**
(hook, length, subtitles, headline restraint, spotlight, framing, ≤3 overlay layers, on-screen text ≥14 px, brightness, ONE CTA,
cursor off end card, callouts). Report its score + the MANUAL items (music licence, VO, facts/brand review, phone viewers) to the user.
Verify before reporting: `python3 $S/shot_qa.py site/index.html` (0 framing issues) and `python3 $S/camera_qa.py site/index.html` (0 direction reversals = no jitter) — both run BEFORE rendering, in seconds; `python3 $S/flicker_check.py frames_zh` (0 spikes), extract frames at transitions (`ffmpeg -ss T -i out.mp4 -frames:v 1 x.png`) and Read them;
`max_volume` should be ≤ -1 dB. Say plainly what was and wasn't checked (e.g. "didn't watch/listen end-to-end").
Keep previous versions (suffix `_v2`) rather than overwriting unless asked to replace.

## Quality bar (what moved the score from 6.5 → ~8.5)
| Problem in v1 | Fix |
|---|---|
| Whole window always visible, 17px text unreadable on mobile | camera push-ins per beat (scale 1.3–1.8), engine `cam` keyframes |
| Emoji icons | Lucide SVG icons via `H.I()` |
| Logo and window cross-dissolving (muddy) | sequential: logo zooms+blurs out, THEN window rises with 3D tilt |
| Empty space / distracting lower content during early beats | collapse hidden rows' height; fade unrelated sections in only when their beat starts |
| Two text layers cross-fading on tab switch | out (0.2s) then in (0.3s), with ±80px slide |
| Caption over busy UI | opaque pill + `#topfade` gradient under it |
| Silent interactions | SFX timeline (clicks, pops, typing ticks, whooshes on camera moves, chime on success) |
| Thin synthesized music | `music_pro.py` cue-scored arrangement + lookahead ducking (measured speech SNR median 24–30 dB) |
| Feature list with no story / no ending ask | persona + time-of-day clock, outcome stats from the story, CTA pill (see engine.md "Persuasion & depth") |
| Flat, single-plane motion | match-cut logo flight, lift-off elements, parallax bg/foreground |
| Viewer's eye wanders; everything equally bright | `spotlight:{}` in Demo.init — dim+blur outside the camera's hold target |
| Close-ups lose the whole-app context / empty canvas around the app | `camBounds:'#win'` for BOTH modes: wide shots = app 90 % with equal margins, close-ups fill 100 %; no minimap (it adds clutter); keep each shot's target inside one panel group (editor OR chat) so it fits at fill scale |
| Camera cuts every 2–3 s, viewer feels dragged around | one shot per VO beat (5–8 s holds) framing the work area; `spots` move focus inside the hold; fast moves ≤ 15% of runtime |
| Remaining gap to 9+ | licensed/composed music for public launch; 1–2 real recorded clips from a demo account |

Pitfalls: see `references/pitfalls.md` (3D blur, zsh word-splitting, Playwright browser, Polly timing…).
