# Audio: voiceover, subtitles, SFX, music, beats

`S=~/.claude/skills/demoreel/scripts`.

Any TTS engine (azure / elevenlabs / openai / polly / kokoro local / say) + subtitles for any engine or a human VO — docs/voiceover.md.
`PY=~/.cache/demoreel-venv/bin/python` = ONE venv with BOTH requirements files (`pip install -r requirements.txt -r requirements-voice.txt`),
so tts / align_subs / audio_qa all run in it (a voice-only venv lacks scipy → audio_qa fails).
- **Generate the VO AND align the subtitles right after the script is approved, as ONE background job, while you build the
  page** (`for L in zh en; do $PY $S/tts.py … && $PY $S/align_subs.py …; done &`) — together ~1 min for two languages and then
  off the critical path. Cloud TTS speed is bounded by the account's requests-per-minute quota (Polly: 16 lines ≈ 40 s, no RPM issues; MiniMax ≈ 50 s, quota-bound);
  tts.py retries rate limits itself (HTTP 429 / MiniMax 1002: 20/40/65/65 s backoff) and then paces requests 3.5 s apart
  (`TTS_MIN_INTERVAL` to preset it). Run languages sequentially, not in parallel. Don't run align_subs concurrently with
  render_parallel — both are CPU-bound (measured: saves ~5 s of 47 s). Fix every "ends …s, next starts …s" WARN and any last line ending after the duration by
  shortening the text, then regenerate only that language.
```bash
$PY $S/tts.py vo_zh.tsv vo_zh.wav --lang zh --duration 30   # DEFAULT = Polly (Zhiyu neural; en: Ruth generative) → + vo_zh.manifest.json (−19 LUFS)
$PY $S/tts.py vo_en.tsv vo_en.wav --lang en --duration 30   # other engines: --provider kokoro|minimax|azure|elevenlabs|openai|say
$PY $S/align_subs.py vo_zh.manifest.json site/subs_zh.json --lang zh --keywords "…"   # faster-whisper word timing (cached model, offline), script text kept
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
python3 $S/beat_grid.py site/beats.js --bpm 120 --start 5 --dur 30  # cut on the beat: procedural score → exact grid (anchored at 0 s)
python3 $S/beat_grid.py site/beats.js --wav licensed.wav            # licensed/generated track → tempo + phase detected (±15 ms on 4/4)
# engine snaps camera-move arrivals + headline starts to beats within 0.15 s; commercial_qa reports 'beat sync' (≥ 60 % on the beat)
# keep score cues on the grid (multiples of 60/bpm): at 90 BPM --groove 5.0 is half a beat off → 5.33
$PY $S/audio_qa.py music.wav vo.wav --gain 0.2                  # arc / sub share / speech-band SNR (p5 >= 10 dB)
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
