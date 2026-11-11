# Opening library (first 3 s) — pick per film, never by habit

The first 3 s decide whether a feed viewer stays. Every film needs a hook, but NOT the same hook: reusing one opening makes a
product's films look templated. At checkpoint 2 propose 2–3 openings that fit THIS feature (with the ASCII sketches below), let
the user pick, and record the choice in the project's `demo_notes.md`. For the same product, default to a different opening
than the last film unless the user asks to repeat.

| Opening | First 3 s on screen | Fits | Built-in | Build with |
|---|---|---|---|---|
| **Text / kinetic question** | one question, chunk-by-chunk on the beat | muted feeds, abstract pain | `?hook=text` | `H.kinetic` |
| **Result first** | the finished output (draft, table, report) → "How did this happen?" | AI generation features | `?hook=result` | `H.reveal` + `H.stream` + `H.kinetic` |
| **Before / after split** | left: tedious manual work + running clock; right: done in one line | time-saving workflows | `?hook=split` | `H.reveal` + `H.count` + `H.stream` |
| **Time contrast** | old duration struck out → new duration | efficiency claims WITH a real/story number | `?hook=timer` | `H.reveal` + `H.strike` |
| **Inside the product** | no intro — close-up on the key action (typing, pressing Send), pull back at ~3 s; logo only at the end or as a corner badge | products whose interaction is the wow | (restructure) | `camIn:[0,0.4]`, first cam key = close-up |
| **Persona moment** | person + clock + ONE decisive message ("Boss: which one by 9 AM?") | story spots, B2B scenarios | (page) | `H.reveal`, persona pill |
| **Chaos → order** | many notifications/files fly in, then collapse into the logo | overload / scattered-information pain | (examples) | chaos cards (see the feed/chat examples) |
| **Macro pull-back** | extreme close-up on one detail (cursor, a number) slowly widening to the app | launch / brand films | (page) | camera keys only |

Rules
- One idea, readable in < 1.5 s (`commercial_qa` "hook" checks text on screen at 1.5 s); no logo-only opening.
- Numbers in a hook (timer, split clock) come from the user or the story itself — never invented product metrics.
- Logo placement is part of the choice: after the hook (3–5 s), only on the end card (social cuts), or as a corner badge.
- Vary the transition into the UI too: logo match-cut, hard cut on a beat, the hook card morphing into the real UI element.
- Sound: give each opening its own first sound (kinetic: ticks on chunks; result: soft chime; split: clock ticks; timer: strike swish).

ASCII sketches for checkpoint 2 (use them as AskUserQuestion `preview`s)
```
text                    result first              split                       timer
┌──────────────────┐    ┌──────────────────┐     ┌────────┬─────────┐       ┌──────────────────┐
│                  │    │ ┌──────────────┐ │     │ manual │ Acme    │       │                  │
│  Hundreds of     │    │ │ ✦ AI summary │ │     │ ▭ mail │         │       │  2̶ ̶h̶o̶u̶r̶s̶  2 min  │
│  messages.       │    │ │ The contract │ │     │ ▭ cal  │ "The    │       │  to find today's │
│  Where do you    │    │ │ is urgent…   │ │     │ ▭ sheet│ contract│       │  priorities      │
│  start?          │    │ └──────────────┘ │     │ 47:12 ⏱│ …"  ✓   │       │                  │
│                  │    │ How did this     │     └────────┴─────────┘       └──────────────────┘
└──────────────────┘    │ happen?          │
                        └──────────────────┘
```
Preview the built-in ones: `python3 $S/preview_sheet.py templates/demo.html /tmp/hooks.png --lang en 0.7 1.6 2.4` with
`?hook=` set in the page (or copy the template and set `HOOK`).
