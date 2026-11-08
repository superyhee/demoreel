#!/bin/bash
# Offline fallback VO (robotic; for timing drafts). usage: tts_say.sh <script.tsv> <out.wav> [voice] [rate] [duration=30]
#   macOS: `say` (zh voice Tingting, en Samantha; rate = words/min, e.g. 210)
#   Linux: `espeak-ng` (voice e.g. cmn / en-us; rate = words/min, e.g. 160)
set -e; TSV=$1; OUT=$2; VOICE=$3; RATE=$4; DUR=${5:-30}; W=$(mktemp -d); i=0; inputs=(); filt=""; mix=""
if command -v say >/dev/null; then ENG=say; VOICE=${VOICE:-Tingting}; RATE=${RATE:-210}
elif command -v espeak-ng >/dev/null; then ENG=espeak; VOICE=${VOICE:-cmn}; RATE=${RATE:-160}
else echo "need macOS say or espeak-ng" >&2; exit 1; fi
while IFS=$'\t' read -r st text; do [ -z "$text" ] && continue
  if [ $ENG = say ]; then say -v "$VOICE" -r "$RATE" -o $W/v$i.aiff "$text"; f=$W/v$i.aiff
  else espeak-ng -v "$VOICE" -s "$RATE" -w $W/v$i.wav "$text"; f=$W/v$i.wav; fi
  echo "$i start=$st dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $f) $text"
  ms=$(python3 -c 'import sys;print(int(float(sys.argv[1])*1000))' "$st"); inputs+=(-i $f); filt+="[${i}]adelay=${ms}|${ms}[a${i}];"; mix+="[a$i]"; i=$((i+1)); done < "$TSV"
ffmpeg -v error -y "${inputs[@]}" -filter_complex "${filt}${mix}amix=inputs=$i:normalize=0,aformat=channel_layouts=stereo:sample_rates=44100,apad=whole_dur=$DUR" -t $DUR "$OUT"; echo "vo -> $OUT ($ENG)"
