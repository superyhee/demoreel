# Pitfalls hit in practice (and fixes)

## Rendering
- **Parallel render**: use `render_parallel.py` (segment split, per-segment ffmpeg pipe, concat -c copy). Scales to ~6 workers on M2 Max (≈37 fps); bottleneck is capture+encode, not GPU. Cap x264 threads per worker (RP_X264_THREADS=2) or the encoders starve each other.
- **Laptop screen shorter than 1080 px** → some Chrome instances lay out at the screen height (993 px) and raw CDP captures repeat rows at the bottom. Pin `screen` + `Emulation.setDeviceMetricsOverride(screenWidth/Height)` BEFORE navigation and abort if `innerHeight != 1080` (render_parallel.py does). Verify segment boundaries by PSNR vs a reference render when changing the pipeline.
- **3D transforms blur text.** Chrome rasterizes a `rotateX/rotateY` layer at 1× and upscales it under `scale(1.6)` → soft text. The engine only applies 3D during camIn/camOut (motion hides it); holds use pure 2D transforms → crisp. Always crop a zoomed frame at full res to check.
- **Playwright bundled Chromium missing** (`Executable doesn't exist ... chromium-1140`): use `p.chromium.launch(channel='chrome')` (system Chrome). Don't spend time on `playwright install`.
- **Determinism**: no CSS transitions/animations, no `Date.now()`, no rAF. Everything derives from `t`. Fonts: wait ~600–800 ms after `goto` before frame 0.
- Throughput: ~9 fps screenshotting PNG at 1080p → 900 frames ≈ 100 s. Two languages in parallel with `&` + `wait`.
- Re-render only a broken range with `--from/--to` instead of the whole video.
- `filter: blur()` on `#cam` is only set when > 0.35px; otherwise `none` (keeps holds crisp).

## Camera
- **Zoom jitter** (real AI-IDE test 1:48, close-up → wide): a per-frame clamp blended by scale toggled on/off while the scale hovered around the fill scale → the centre oscillated. Fix: clamp close-up keyframes once; clamp per frame only between two close-ups (and keep scale ≥ fill there); close↔wide moves interpolate between already-clamped keyframes. Detect with `camera_qa.py` (exact geometry, every frame) — pixel edge-trackers on rendered frames give false reversals when the tracked edge changes.
- When editing engine.js with string replacement, re-check that no neighbouring functions were cut (a too-wide replacement once deleted zoomPath/segOf/camAt/curPos) — `node -e new Function(...)` only checks syntax, so also run camera_qa/preview.
- **Empty half-screens in real footage** (real-footage test: the app filled only 59 % of the screen on median, 47 % worst — a chat panel at the window's right edge was centred, leaving the right 40 % blank). Fix: `camBounds:'#win'` (zoomed shots get ≥ fill scale; viewport clamped inside the app; blends in smoothly) → 100 % median. Measure coverage by sampling `#win` rect vs the 1920×1080 stage.
- **Transition QA (do it every render)**: `flicker_check.py frames/` → 0 spikes and max single-frame Δ ≤ ~8 (on light UIs). Causes found so far and their fixes: pull-back exposing a white pane (→ van Wijk path), auto spotlight fading between holds (→ morph across holds), hard editorial cuts dark→white (→ footage_edit crossfades), app repaint flashes in sped-up footage (→ footage_prep de-flash), sudden real UI steps like opening a white document (→ footage_prep 6-frame dissolve). the AI IDE real-footage test: 16 spikes / Δ46.6 → 0 / Δ6.8.
- **Spotlight flicker**: back-to-back spots that each fade out/in (or auto→explicit handoff) drop the dim for a few frames → whole frame flashes +17–31% brightness. Engine now CHAINS spots ≤0.6 s apart (box morphs, dim constant) and disables auto spotlight when `spots` is set. Spot targets must include already-visible content (don't light empty lines that haven't appeared yet). Verify with `scripts/flicker_check.py frames/`.
- **Too many shots feels frantic** (user feedback on the AI-IDE film v4: 28 shots in 76 s, avg hold 2.8 s, camera moving 42%). Rule: **one shot per VO line / narrative beat** (holds 5–8 s), frame the *work area* (e.g. editor + chat) at ~1.2×, and move attention INSIDE the hold with explicit `spots` instead of camera moves. Target: fast camera moves ≤ 15% of runtime. Keep `spots` timing aligned with which view/tab is visible.
- Only close-ups → viewers lose the app context. Use `maxZoom` + `viaWide` + `minimap` (engine.md).
- A target that is `display:none` gives an empty rect → camera flies to the stage origin. Fixed in engine (measure at keyframe time); in custom code, never fit an empty union.

## Real footage
- **Three coordinate spaces — don't mix them**: (a) the 1600-px `_small.png` you look at, (b) macOS logical points (cliclick/osascript; = small × screenW_pt/1600), (c) footage pixels after crop/scale (= screen px × footage_w/crop_w − crop offset). Hotspots measured on (a) but converted as (b) were 5.5 % off → the spotlight cut off the left edge of the chat text. Measure hotspots on a frame of the PREPPED footage itself when in doubt.
- Panels that touch the window edge: hotspot boxes must reach that edge (e.g. chat panel → window right edge), otherwise the spotlight clips one side; check symmetry with hotspot_overlay.py (real-footage test: right side was ~100 px short).
- Crop the macOS Dock by measuring it on the footage (it overlaps the window bottom by ~20–40 px).
- Playwright `record_video` needs an extra ffmpeg download → record_web.py uses Chrome's own `Page.startScreencast` (frames only arrive when the page changes; frames are held to the next timestamp, then resampled to 30 fps).
- Headless recordings contain no OS cursor; use the engine cursor on hotspots.
- Spotlight on a WHITE recording swings brightness ~5× more than on a dark UI (Δ16/frame) → dim 0.3 and 1.0/0.8 s fades (Δ≤6). Check with flicker_check.py and the 'max single-frame Δ'.

## Layout
- Hidden rows that only have `opacity:0` still take space → big empty card. Animate `height` too.
- Content measured once at init (e.g. AI draft box with empty text) gets clipped once text is typed → measure live each frame.
- Long English strings overflow fixed-width cards; use `white-space:nowrap` + wider cards, or shorten copy.
- Big hook text vs badges/cards: give the headline `z-index` above cards and a white `text-shadow` glow; re-position badges per language (en headline is 2 lines).
- Caption pill must be opaque (`#fff`), plus `#topfade` — zoomed UI otherwise shows through.

## Shell / tools
- **zsh doesn't word-split** `$T` → `python3 x.py $T` passes one arg. Use bash scripts with arrays, or literal args.
- ffmpeg `crop=w:h:x:y` (colons, not commas).
- `xstack` needs explicit layout; `scripts/preview_sheet.py` (PIL) avoids that.
- Desktop clicks: `cliclick c:x,y` uses logical points; retina screenshots are 2× pixels. Map via the 1600px preview: `x_logical = x_small * (pixelWidth/2)/1600`.

## Audio
- **Camera-move whooshes on every move feel cheap and tiring** (user feedback on the AI-IDE demo: 27 whooshes / 120 s). Engine default is now sparse (`camSfx:{minGap:8,gain:0.2}`); for long demos with frequent moves use `camSfx:'off'` and add whooshes only on real scene changes (≈1 per 15–25 s).
- sfx.py used to peak-normalise each track → removing events made the remaining ones LOUDER. Now a fixed absolute gain (`SFX_FIXED_GAIN`, default 0.65). Compare SFX versions by RMS, not by peak.
- Polly: Ruth/Matthew support `generative` (most natural en). Zhiyu is `neural` with `--language-code cmn-CN`. Clips include little leading silence; start each line ~0.2s into its beat.
- Opening line is usually too long for a 3s hook → shorten ("Hundreds of messages. Where do you start?").
- Duck music under VO with `sidechaincompress` (in mix.sh); final `loudnorm I=-16 TP=-1.5`.
- Plain sidechain ducks too late → first syllable of each line masked. Use lookahead (VO advanced 150 ms as the key).
- Glue compression on the music master flattens the build (main=lift=peak). Use gentle ratio + explicit section gain automation.
- Risers/snare rolls in the lift usually overlap a VO line — keep them low.
- Bedrock has no music-generation model (checked Nov 2026); ChatCut `music` skill needs its MCP. Fallback = music_pro.py.
- macOS `say` (Tingting) works offline but sounds robotic — fine for timing drafts only.

## Process / safety
- The user's real app shows real colleague/customer data → never put raw captures in a publishable video without asking; default to rebuilt UI + fictional data (fictional company e.g. 星河科技 / Nova Tech, names Wei/Lisa/Kevin).
- Use the user's real logo (cropped), real colors/fonts; don't invent brand elements.
- Report honestly: which frames were checked, that the full video wasn't watched/listened end-to-end, what still separates it from "professional" (music, real footage).

## Cursor tracking / erase (real recordings)
- Logged action times ≠ footage times (easing, edits, crossfades): snap clicks to pointer arrival (engine does it, `snap` 1.2 s).
- Pointer templates must not include background pixels; light and dark UIs need separate I-beam templates (no outline on white).
- Thin templates (I-beam) match static glyphs/rules at ~0.08 → per-kind `thr` 0.04.
- Pointer resting on text for the whole clip → no clean donor frame; inpaint smears glyphs. Re-render the line in the UI font
  (Chrome, DPR 2 → downscale 0.5, fit size by matchTemplate) and paste ONLY inside the erased rectangle.
- Typing cover must extend past the line end (`pad`) or the frozen frame's own caret shows as a thin line.

## Engine-injected element ids
- The engine injects ids into the page: #cap #cursor #ripple #topfade #spot #sb0-3 #mm #subs #speed #tcur #tring #ty*_* #tyc* #dnB* #dnL*.
  A page element with the same id gets restyled by the engine (seen: callout ids #nb1 hijacked the page's "next" button → giant
  purple block). Keep page ids distinct; engine uses the dn*/ty*/t* prefixes for that reason.

## Readability of rebuilt UIs (phone viewers)
- Spotlight dim ≤ 0.35 and blur ≤ 1.2 on dark UIs (0.55 + 2.2 made the whole film murky: mean luma 27 → 35 after the fix).
- Body text ≥ 16 px on screen at close-up scale. Easy global fix: `#win{zoom:1.15}` and divide the window's CSS width/height/left/top
  AND every fixed-px panel width by 1.15 (otherwise panels overlap); then shrink only fixed-width content that overflows
  (diagram, long lists) with a local zoom, and re-run shot_qa (targets get bigger → may no longer fit at fill scale).
- Lift dark theme surfaces a little (panel/editor +7–8 L, muted text ≈ #aeaabd) — real dark UIs look darker on video than on a monitor.

## Light UIs (white SaaS)
- Spotlight on a light UI = a LIGHT veil (`color:'250,248,255', dim≈0.4`), never a dark dim — dark dim turns white UIs muddy grey-purple.
- Callout labels: put them on the side with empty space ('right'/'bottom'); 'top' often lands on the row's action buttons.
- Subtitles duplicating big on-screen titles (hook, logo card, end card) → `subtitles.mute:[[a,b]]`.
- Polly generative voices return no speech marks → subtitle_marks.py falls back to neural timings; render that VO with the neural
  voice too, or the words drift.

## End card text shimmer
- Never slow-zoom/pan a card that holds text (scale 1→1.03 over seconds): text re-rasterises at a new sub-pixel scale each frame and
  visibly jitters. Animate the entrance, then hold perfectly still; keep slow motion for the background (orbs, gradients).
  commercial_qa.py "end card stable" flags sustained sub-pixel drift.
