#!/bin/bash
# Build a timed voiceover track with Amazon Polly.
# usage: tts_polly.sh <script.tsv> <out.wav> [voice] [engine] [lang-code] [duration]
#   script.tsv lines: <start_seconds><TAB><text>      e.g.  5.5	AI writes your daily briefing.
#   voices: en-US Ruth/Matthew (generative|neural), zh: Zhiyu (neural, cmn-CN), ja: Kazuha/Takumi (neural)
# Prints each clip's duration and WARNs when a clip overruns the next start (shorten the line, don't speed up).
set -e
TSV=$1; OUT=$2; VOICE=${3:-Ruth}; ENGINE=${4:-generative}; LC=${5:-}; DUR=${6:-30}
W=$(mktemp -d); i=0; inputs=(); filt=""; starts=(); durs=()
while IFS=$'\t' read -r st text; do
  [ -z "$text" ] && continue
  aws polly synthesize-speech --region us-east-1 --engine $ENGINE --voice-id $VOICE ${LC:+--language-code $LC} \
     --output-format mp3 --sample-rate 24000 --text "$text" $W/v$i.mp3 >/dev/null
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $W/v$i.mp3)
  starts+=($st); durs+=($d); echo "$i start=$st dur=$d  $text"
  ms=$(python3 -c "print(int(float('$st')*1000))")
  inputs+=(-i $W/v$i.mp3); filt+="[$i]adelay=$ms|$ms[a$i];"; i=$((i+1))
done < "$TSV"
python3 -c "import sys;s=[float(x) for x in '${starts[*]}'.split()];d=[float(x) for x in '${durs[*]}'.split()];[print(f'WARN: line {k} ends {s[k]+d[k]:.2f}s, next starts {s[k+1]}s -> shorten it') for k in range(len(s)-1) if s[k]+d[k]>s[k+1]-0.1];print(f'last line ends {s[-1]+d[-1]:.2f}s')"
mix=""; for ((k=0;k<i;k++)); do mix+="[a$k]"; done
ffmpeg -v error -y "${inputs[@]}" -filter_complex "${filt}${mix}amix=inputs=$i:normalize=0,aformat=channel_layouts=stereo:sample_rates=44100,apad=whole_dur=$DUR" -t $DUR "$OUT"
echo "vo -> $OUT"
