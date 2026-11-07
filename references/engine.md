# engine.js API

Load order in the page: strings → `<script src="engine.js">` → your script calling `Demo.init({...})`.
Stage is 1920×1080. Coordinates for cursor points / view are stage pixels.

## Required DOM
```
#stage                    (position:absolute; perspective:2600px)
  ... hook / logo layers (outside #cam)
  #cam > #win             (the rebuilt app window; camera transforms #cam)
  ... end card (outside #cam, animate in post())
```
Engine injects `#cap` (caption pill), `#topfade`, `#ripple`, `#cursor`, `#spot` + 4 `.sb` blur bands — style them in CSS (see templates/demo.html).

## Demo.init(config)
| key | meaning |
|---|---|
| `duration`, `fps` | default 30 / 30 |
| `view` | `{cx,cy,w,h}` safe area targets are fitted into. Default `{960,620,1640,780}` (leaves room for caption) |
| `cam` | `[[t, ['#a','#b'], maxScale, rotX, rotY], ...]` — union rect of selectors is centered & scaled to fit `view`, capped by `maxScale`. Repeat the same selectors at a later t (slightly larger scale) for a slow push during a hold. Interpolation uses quintic ease. rotX/rotY are only applied while entering/exiting (see pitfalls) |
| `camIn`, `camOut` | `[a,b]` window rises from below with 3D tilt + blur / shrinks and blurs out |
| `cursor` | `[[t, '#sel' or [x,y]], ...]` — eased arc path; targets measured AFTER camera transform, so they land on the zoomed element. Hidden outside first/last key and during camIn/camOut |
| `clicks` | `[t,...]` ripple + press scale; auto adds `click` SFX |
| `captions` | `[[a,b,html], ...]` center-out reveal, fades 0.25s before b. Use `<em>` for gradient accent |
| `sfx` | extra `[t,type,gain]` events. Auto-added: click per click, whoosh per camera move between different targets (<1.2s apart) |
| `scene(t,H)` | set ALL UI state for time t (pure function of t). Runs before camera measurement |
| `post(t,H)` | runs last (end cards, overlays outside #cam) |
| `spotlight` | `{dim:.55, blur:2.2, pad:14, feather:40, radius:14, color:'r,g,b', minScale:1.15, skip:['#win']}` — during every camera HOLD (two consecutive keyframes with the same selectors, scale ≥ minScale) the hold targets stay bright/sharp, everything else is dimmed + backdrop-blurred with a feathered edge; off while the camera moves. Set `color` to the stage bg (dark UIs: `'8,6,14'`) |
| `footage` | `[{el:'#rec', src:'rec/f', ext:'jpg', fps, frames, w, h, map:[[projT,footT],...], hotspots:{'#hs-x':[x,y,w,h]}, speedBadge}]` — real-recording layer (an `<img>` inside the window); render(t) returns a Promise until the frame is decoded (Playwright awaits it). Hotspots are invisible divs in footage-pixel coords usable as camera/spot/cursor targets |
| `camBounds`, `wideFill`, `captionSafe`, `bottomSafe` | framing rules: shots whose target IS the bounds selector (e.g. `['#win']`) are WIDE → app spans `wideFill` (0.9) of the limiting dimension, centred with equal margins; other shots with scale>1.05 are CLOSE-UPs → ≥ fill scale, viewport clamped to the app, target kept below `captionSafe` (140 px) and above `bottomSafe` (24 px). Use a tight target (the content, not the whole panel) so it fits the safe area |
| `maxZoom` | global cap on camera scale (e.g. 1.4) — keep neighbouring panels in frame; let the spotlight do the focusing |
| `camRho`, `cutS`, `motionBlurMax` | camera path between shots = **van Wijk–Nuij optimal zoom/pan** (d3.interpolateZoom math): near targets → pan, far → gentle perceptually-constant zoom-out/in; `cutS` → cut instead of flying for very long jumps (or per shot `cam[i][5]={cut:true}`); blur ≤1.5 px. Auto spotlight morphs across consecutive holds (no brightness breathing). |
| `viaWide`, `viaCenter` (superseded) | on moves between different targets, dip the scale toward `viaWide` (e.g. 1.0) and drift the focus `viaCenter` (0.85) toward the window centre → pull back · pan · push in, so viewers see where in the app they travel. Use ≥1.1 s moves |
| `minimap` | `{target:'#win', panels:[['#side','侧栏'],['#edArea','编辑器'],['#chat','Agent']], w:300, pos:[x,y], color, minScale}` — 'you are here' schematic + live viewport box while zoomed |
| `camSfx` | `'off'` or `{minGap:8, gain:0.2}` (default) — auto whoosh on camera moves, throttled. Long demos: `'off'` + manual whooshes on scene changes only |
| `spots` | `[[a,b,['#sel'],dim?],...]` explicit spotlight windows; override the auto spotlight |

After init: `window.render(t)`, `window.SFX`, `window.DURATION`, `window.FPS` (used by render_frames.py).

## Helpers `H` (= `Demo.H`)
- `H.p(t,a,b)` progress 0..1 · `H.eo` ease-out cubic · `H.eio` in-out cubic · `H.eio5` in-out quintic · `H.back` overshoot · `H.lerp`
- `H.pop(t,start,dur)` overshoot scale (0 before start) — tags/badges
- `H.rise(el,t,start,dur,dy)` fade + slide up
- `H.grow(el,k)` animate height 0→natural (element needs `overflow:hidden`; `display:none` at k=0; update its text BEFORE calling) — expanding rows, AI result boxes
- `H.typed(str,k)` typewriter substring · `H.caret(t,a,b)` blinking ▍
- `H.I(name, style?)` inline SVG icon. Names: mail cal msg bell file alert checkc check reply timer pen act lib zap app layers flask db grid flow search spark folder users refresh down right plus ext chart src notes settings upload play plane code. Add more Lucide paths to `H.IC` as needed.

## Patterns (from the Quick example)
- **Chaos hook**: 12–14 notification cards fly in from edges (stagger 0.11s), random depth z∈[0.8,1.1] with blur for far ones, slow push-in, then all converge to center and shrink into the logo.
- **Typing AI output**: `H.typed(TEXT, H.p(t,a,b))` + caret; add `tick` SFX every ~0.07s over [a,b].
- **Expand → act**: chevron click → `H.grow(row)` → highlight "N sources" with a pulse → click "Draft reply" → result box grows + types.
- **Filter**: type query → chips toggle `.on` → non-matching rows collapse height to 0, matches get highlight + soft shadow.
- **Tab switch**: old view out (0.2s, −80px) then new view in (0.3s, +80px). Never cross-dissolve two text layers.
- **Success moment**: button turns filled + confirmation bar pops (`back` ease) + `chime`.
- **End card**: logo pops with rotation, name rises, slogan, then a small tagline row; slow 3% scale drift.
- Measure dynamic heights live in `scene()` (set `height:auto`, read `scrollHeight`, then set px) — measuring once at init breaks when text is typed in later.

## Persuasion & depth patterns (v4 of the Quick example)
- **Persona + time-of-day clock**: top-left pill (avatar · name · role · clock). The clock flips per beat (08:58 → 09:00 → 10:30 → 14:00 → 17:30)
  so the feature list reads as "a day with the product". Clock flip = new text slides up 22px + fade, with a `tick` SFX.
- **Outcome stats from the story itself** on the end card ("3 件要事已排序 · 1 封回复已起草 · 3 小时专注已预留"), with numbers counting up.
  Never invent product-level metrics ("saves 40 min/day") — those need real data from the user.
- **CTA**: gradient pill with a concrete in-app action ("Open Acme → Inbox") + pulse ring. Ask the user for an official URL / QR code before adding one.
- **Match-cut logo flight**: the hero logo shrinks to a hover point, then lands on a matching icon inside the UI (e.g. the briefing ✦) while the
  window rises — two phases, so the moving target doesn't make the path swing. Target rect = `getBoundingClientRect()` AFTER the camera transform.
- **Lift-off (fake Z depth, stays crisp)**: element rises `translateY(-8px) scale(1.03)` with a growing soft shadow on a sin(π·k) curve, synced
  to its tag pop / appearance. Parent cards need `overflow:visible`.
- **Parallax**: background orbs move opposite to the camera at 0.05–0.15×, blurred foreground bokeh at 0.3–0.45× (opacity ≈0.3). Gives depth
  without 3D transforms (which blur text).

- **Camera targets must be height-bounded** (specific lines/cards, e.g. `['#rq5','#rq11']`), not whole panels — a tall panel makes fit() zoom OUT and the spotlight covers everything.
- **Holds**: generate a second keyframe with the same selectors ~0.75 s before the next shot (`SHOTS → CAM` helper in the the AI IDE example) so the camera holds, moves fast, and the spotlight can engage.
- **Keyframe targets are measured at the keyframe's own time** (engine re-runs `scene(K[i].t)` for the two surrounding keyframes each frame). Targets that are `display:none` *now* but visible at the keyframe are framed correctly. Keep `scene` pure in `t`.
