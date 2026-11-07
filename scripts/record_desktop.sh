#!/bin/bash
# Record a DESKTOP app on macOS / Linux (X11, Wayland) / Windows (Git-Bash/MSYS) with ffmpeg at 30 fps.
# usage:
#   record_desktop.sh <out.mp4> <seconds> --window "<App>" "<title substring>"   # auto-locate the window (mac/X11/Win)
#   record_desktop.sh <out.mp4> <seconds> --region X Y W H                        # screen PIXELS (retina = 2× points)
#   add --dry-run to print the command only.   Privacy: the region captures whatever is ON TOP → use a demo project,
#   ask the user not to use the machine, then run footage_mask.py to drop frames where other windows covered it.
set -e; OUT=$1; SEC=$2; shift 2; MODE=$1; DRY=0; [[ " $* " == *" --dry-run "* ]] && DRY=1
OS=$(uname -s); case "$OS" in MINGW*|MSYS*|CYGWIN*) OS=Windows;; esac
if [ "$MODE" = "--window" ]; then APP=$2; TS=$3
  case $OS in
    Darwin) B=$(osascript -e "tell application \"System Events\" to tell process \"$APP\" to get {position, size} of (first window whose name contains \"$TS\")" 2>/dev/null | tr -d ' ') || true
            IFS=, read -r LX LY LW LH <<<"$B"
            SCALE=$(python3 -c "import subprocess,re;o=subprocess.run(['system_profiler','SPDisplaysDataType'],capture_output=True,text=True).stdout;print(2 if 'Retina' in o else 1)")
            X=$((LX*SCALE)); Y=$((LY*SCALE)); W=$((LW*SCALE)); H=$((LH*SCALE));;
    Linux)  WID=$(xdotool search --name "$TS" | head -1); eval $(xdotool getwindowgeometry --shell "$WID"); X=$X; Y=$Y; W=$WIDTH; H=$HEIGHT;;
    Windows) X=; W=;;   # gdigrab can capture a window by title directly
  esac
elif [ "$MODE" = "--region" ]; then X=$2; Y=$3; W=$4; H=$5; fi
if [ "$OS" != Windows ] && { [ -z "$W" ] || [ "${W:-0}" -le 0 ] || [ "${H:-0}" -le 0 ]; }; then echo "ERROR: window/region not found (no recording made)" >&2; exit 2; fi
W=$((W/2*2)); H=$((H/2*2))
case $OS in
  Darwin) IDX=$(ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep -m1 "Capture screen" | sed -E 's/.*\[([0-9]+)\] Capture screen.*/\1/')
          CMD=(ffmpeg -v error -y -f avfoundation -framerate 30 -capture_cursor 1 -i "${IDX}:none" -t "$SEC" -vf "crop=$W:$H:$X:$Y,fps=30");;
  Linux)  if [ -n "$WAYLAND_DISPLAY" ] && command -v wf-recorder >/dev/null; then CMD=(timeout "$SEC" wf-recorder -g "$X,$Y ${W}x$H" -r 30 -f)
          else CMD=(ffmpeg -v error -y -f x11grab -framerate 30 -video_size ${W}x$H -i "${DISPLAY:-:0}+$X,$Y" -t "$SEC"); fi;;
  Windows) if [ -n "$TS" ]; then CMD=(ffmpeg -v error -y -f gdigrab -framerate 30 -i "title=$TS" -t "$SEC")
           else CMD=(ffmpeg -v error -y -f gdigrab -framerate 30 -offset_x $X -offset_y $Y -video_size ${W}x$H -i desktop -t "$SEC"); fi;;
esac
CMD+=(-c:v libx264 -crf 14 -preset veryfast -pix_fmt yuv420p "$OUT")
[[ "${CMD[0]}" == timeout ]] && CMD=("${CMD[@]:0:7}" "$OUT")
if [ $DRY = 1 ]; then printf '%q ' "${CMD[@]}"; echo; exit 0; fi
"${CMD[@]}"; echo "recorded $OUT (${W}x${H} @ $X,$Y, ${SEC}s, $OS)"
