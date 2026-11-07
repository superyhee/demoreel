# Benchmarks: what great commercial product demos do

Use as a pre-script checklist. (Patterns distilled from well-known launch films — Apple product films, Linear/Raycast/Arc
launch videos, GitHub Copilot / Cursor / Vercel Ship demos, Dropbox/Loom/Notion explainers, Slack/Notion AI story spots.
Claude cannot watch videos; for a shot-by-shot teardown ask the user for links + transcript or frames.)

| Archetype | Signature moves |
|---|---|
| Brand film (Apple) | one idea per shot; camera/light/music locked to the beat; almost no text; benefits not specs |
| SaaS launch (Linear, Raycast, Arc) | UI is the hero; UI layers exploded/parallaxed and re-assembled in space; 2–3 s cuts; SFX on every interaction; restraint = taste |
| Developer tool (Copilot, Cursor, Vercel) | real screen capture + zoom; AI "thinking" shown sped-up, not cut (credibility); real repo/task; verifiable ending (tests pass, deploy live) |
| Explainer (Dropbox, Loom, Notion) | one person's concrete pain; one scenario end-to-end; conversational VO like a colleague showing you |
| Story spot (Slack, Notion AI) | character + conflict + turn; product enters as the tool that resolves it; emotional arc anxious → smooth → relieved |

## 8-point checklist (score each 0/1 before rendering)
1. **First 3 s**: a pain image or a surprising result — never open on the logo.
2. **One storyline**: one person, one task, start → finish. Features are props in the plot, not a list.
3. **Real > rebuilt**: at least 2–3 real recorded clips (demo account) for dev tools / AI products; show waiting sped-up.
4. **Framing by shot type** — WIDE (establishing / transitions / end): app spans ~90 % of the frame's limiting dimension with EQUAL margins on a designed background; CLOSE-UP (feature beats): app fills 100 %, target below the caption band, edges cut at panel borders. Open every film with a 1.5–2 s wide hold before the first push-in. Never one-sided emptiness. Check with `shot_qa.py`.
   Previously: **Frame always full**: when zoomed in, the app fills the screen — never empty canvas beside it (engine `camBounds`). A target near the app edge sits off-centre with dimmed context; deliberate negative space only as a designed layout (lifted card + headline).
5. **One focus at a time**: dim/blur everything outside the focus (spotlight), camera tells the viewer where to look.
5. **Every beat ends in a visible result**: checkmark, counter, page live.
6. **Sound is half the film**: cut on the music beat; SFX per interaction; VO sounds spoken, not read.
7. **Restraint**: cut ~20% of caption cards; let some beats run on picture + music only.
8. **One CTA** at the end (download / try / book a demo) — never three.

## Common gaps in our pipeline (as of the 2-min AI-IDE film)
- No real footage (biggest credibility gap) → ask the user for a demo-account run to record.
- ~~No spotlight dimming outside the focus~~ → done: `spotlight` option in engine.js.
- Late beats (pricing, import) drift off the storyline → merge into the plot or cut; consider a 90 s cut.
