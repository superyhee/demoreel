# Real footage (REAL / HYBRID modes)

Read when the footage mode is REAL or HYBRID. `S=~/.claude/skills/demoreel/scripts`.

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

## Recording → footage layer (preferred for dev tools / AI products — credibility)
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

## Lessons from the DemoReel launch film (terminal-heavy HYBRID)
- `record_terminal.sh COLS ROWS`: pick COLS so the longest output line fits (140+ for QA-style logs) — wrapped lines break
  mid-word on screen. Then frame close-ups on the LEFT part of the log (hotspot ≈ 60 % of the width, scale ≈ 1.75): the
  status words (PASS/FAIL, key names) stay ≥ 24 px; line tails may crop.
- An inset recording (image smaller than its panel) is fine: hotspots are placed in the image's own box.
- Show the RESULT of every beat on screen: a FAIL → fix → PASS sequence reads far better than a FAIL alone.
- 9:16 of a wide terminal does not work by reframing: record a separate narrow session (≈ 60 cols) and give the vertical cut
  its own `aspects:{'9:16':{cam:[…]}}`.
- Label simulated UI on screen ("simulated demo, fictional data") when real and rebuilt footage share a film.

