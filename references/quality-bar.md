# Quality bar (what moved the score from 6.5 → ~8.5)

Use when scoring a film or deciding what to fix next.

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
| Text shimmers/jitters while the camera "moves" | still holds (engine default), H.reveal/H.settle snap ease tails, shadow-only lifts, fixed layout for held targets — gate: commercial_qa `hold still` |
| Every film opens the same way | hook library `references/hooks.md`, 2–3 options per storyboard, opening logged in demo_notes.md, `?hook=` variants in the template |
| Camera cuts every 2–3 s, viewer feels dragged around | one shot per VO beat (5–8 s holds) framing the work area; `spots` move focus inside the hold; fast moves ≤ 15% of runtime |
| Remaining gap to 9+ | licensed/composed music for public launch; 1–2 real recorded clips from a demo account |
