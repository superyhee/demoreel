#!/bin/bash
# Record a region of the macOS screen (for DESKTOP apps) with ffmpeg/avfoundation at 30 fps.
# usage: record_mac.sh <out.mp4> <x> <y> <w> <h> <seconds> [screen_index=auto]
#   x/y/w/h in PIXELS of the screen capture (retina = 2x logical points; check with: screencapture + sips -g pixelWidth)
# Needs Screen Recording permission for your terminal (System Settings → Privacy & Security → Screen Recording).
# Close/hide anything private first and use a demo account. List devices: ffmpeg -f avfoundation -list_devices true -i ""
set -e; OUT=$1; X=$2; Y=$3; W=$4; H=$5; SEC=$6; IDX=${7:-$(ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep -m1 "Capture screen" | sed -E 's/.*\[([0-9]+)\] Capture screen.*/\1/')}
ffmpeg -v error -y -f avfoundation -framerate 30 -capture_cursor 1 -i "${IDX}:none" -t "$SEC" -vf "crop=$W:$H:$X:$Y,fps=30" -c:v libx264 -crf 14 -preset veryfast -pix_fmt yuv420p "$OUT"
echo "recorded $OUT (${W}x${H}, ${SEC}s, screen $IDX)"
