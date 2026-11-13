#!/bin/bash
# Record a CLI / terminal tool with REAL output, crisp text, no desktop capture: asciinema (scripted) → agg → mp4.
# usage: record_terminal.sh <out.mp4> <script.sh> [cols=110] [rows=30] [theme=monokai] [font_size=26]
#   script.sh = the commands to run (use a demo dir/account). Add `sleep` between commands for pacing; for typing effects
#   use a helper like: type(){ for ((i=0;i<${#1};i++)); do printf '%s' "${1:i:1}"; sleep 0.04; done; echo; eval "$1"; }
set -e; OUT=$1; SCR=$2; COLS=${3:-110}; ROWS=${4:-30}; THEME=${5:-monokai}; FS=${6:-26}; T=$(mktemp -d)
# asciinema 3.x: --window-size COLSxROWS; 2.x: --cols/--rows. Never fall back silently to the default 80×24 — lines then
# wrap mid-word in the film.
if asciinema rec --help 2>&1 | grep -q -- '--window-size'; then
  asciinema rec --overwrite -q --window-size "${COLS}x${ROWS}" -c "bash '$SCR'" "$T/rec.cast"
else
  asciinema rec --overwrite -q --cols "$COLS" --rows "$ROWS" -c "bash '$SCR'" "$T/rec.cast"
fi
agg --theme "$THEME" --font-size "$FS" --fps-cap 30 --idle-time-limit 2 "$T/rec.cast" "$T/rec.gif"
ffmpeg -v error -y -i "$T/rec.gif" -vf "fps=30,scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos,format=yuv420p" -c:v libx264 -crf 14 "$OUT"
echo "recorded $OUT ($(ffprobe -v error -show_entries stream=width,height -of csv=p=0 "$OUT"), $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")s)"
