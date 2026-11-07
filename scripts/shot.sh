#!/bin/bash
# Screenshot the whole screen for app exploration. usage: shot.sh <out_basename> [app name to activate (macOS)]
# Writes <name>.png (full res) and <name>_small.png (1600 px wide, for viewing).
# macOS: screencapture (+ osascript to activate the app). Click with: cliclick c:<x>,<y> (logical points;
#        logical = small_x * (pixelWidth/2)/1600 on retina).
# Linux/X11: import (ImageMagick) | scrot | maim ; click with: xdotool mousemove X Y click 1
# Linux/Wayland: grim ; click with: ydotool (needs ydotoold)
set -e; OUT=$1; APP=$2
case "$(uname)" in
  Darwin) [ -n "$APP" ] && osascript -e "tell application \"$APP\" to activate" && sleep 1
          screencapture -x "$OUT.png" ;;
  Linux)  if [ -n "$WAYLAND_DISPLAY" ] && command -v grim >/dev/null; then grim "$OUT.png"
          elif command -v import >/dev/null; then import -window root "$OUT.png"
          elif command -v scrot >/dev/null; then scrot -o "$OUT.png"
          elif command -v maim >/dev/null; then maim "$OUT.png"
          else echo "no screenshot tool: install imagemagick, scrot, maim or grim" >&2; exit 1; fi ;;
  *) echo "unsupported OS $(uname)" >&2; exit 1 ;;
esac
python3 -c "from PIL import Image;im=Image.open('$OUT.png');w,h=im.size;im.resize((1600,int(h*1600/w))).save('${OUT}_small.png');print('${OUT}_small.png',w,h)"
