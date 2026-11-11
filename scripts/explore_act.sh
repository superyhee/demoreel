#!/bin/bash
# One exploration step on a desktop app (macOS), privacy-safe and focus-safe:
#   1. find the app's window (win_info.sh), 2. bring it to front and VERIFY it is frontmost (terminals, chat apps, agent UIs
#   steal focus between calls) — re-verified immediately before the action, 3. act, 4. screenshot ONLY that window
#   (screencapture -l <id>), so another app coming to front can never leak into the shot.
# usage: explore_act.sh <app> <window-title-substr|-> <out_basename> [click X,Y | scroll X,Y,N,up|down | key <cliclick kp:..> | none]
#   X,Y = pixels in the PREVIOUS shot's <out>_small.png (1600 px wide, window only) → converted to screen points using the
#   window's CURRENT position, so a window that moved is still hit correctly.
# e.g.   explore_act.sh "Acme" - shots/s0 none                  (first look)
#        explore_act.sh "Acme" - shots/s1 click 120,95          (coords read off shots/s0_small.png)
#        explore_act.sh "Acme" - shots/s2 scroll 900,400,60,up
# Writes <out>.png (full res) + <out>_small.png; exit 1 = focus could not be secured (nothing was clicked).
set -uo pipefail
APP=$1; TS=$2; OUT=$3; ACT=${4:-none}; ARG=${5:-}; D=$(cd "$(dirname "$0")" && pwd)
front(){ osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true'; }
ready(){   # frontmost app is $APP and (optionally) its front window title contains $TS
  [ "$(front)" = "$APP" ] || return 1; [ "$TS" = "-" ] && return 0
  W=$(osascript -e "tell application \"System Events\" to tell process \"$APP\" to get name of front window" 2>/dev/null); [[ "$W" == *"$TS"* ]]; }
secure(){ for _ in 1 2 3 4; do osascript -e "tell application \"$APP\" to activate" >/dev/null 2>&1; sleep 0.8; ready && return 0; done; return 1; }
[ "$ACT" = none ] || secure || { echo "ABORT: $APP not frontmost after 4 tries (frontmost=$(front)) — nothing clicked; ask the user to leave the machine alone or use a separate Space" >&2; exit 1; }
read -r WID WX WY WW WH < <("$D/win_info.sh" "$APP") || { echo "ABORT: no window for $APP" >&2; exit 1; }
pt(){ python3 -c 'import sys;x,y,wx,wy,ww=map(float,sys.argv[1:]);k=ww/1600;print(f"{round(wx+x*k)},{round(wy+y*k)}")' "$1" "$2" "$WX" "$WY" "$WW"; }
if [ "$ACT" != none ]; then
  ready || secure || { echo "ABORT: focus lost right before the action — nothing done" >&2; exit 1; }
  case "$ACT" in
    click)  IFS=, read -r x y <<<"$ARG"; cliclick -e 200 "c:$(pt "$x" "$y")" ;;
    scroll) IFS=, read -r x y n dir <<<"$ARG"; IFS=, read -r sx sy <<<"$(pt "$x" "$y")"; "$D/scroll_mac.sh" "$sx" "$sy" "$n" "$dir" ;;
    key)    cliclick "$ARG" ;;
    *) echo "unknown action $ACT" >&2; exit 2 ;;
  esac
  [ "$(front)" = "$APP" ] || echo "WARN: focus moved to $(front) around the action — verify in the screenshot that it landed in $APP" >&2
fi
sleep "${WAIT:-1.2}"
read -r WID WX WY WW WH < <("$D/win_info.sh" "$APP")
screencapture -x -o -l "$WID" "$OUT.png" || { echo "screencapture failed (Screen Recording permission for this terminal?)" >&2; exit 1; }
python3 -c "from PIL import Image;im=Image.open('$OUT.png');w,h=im.size;im.resize((1600,int(h*1600/w))).save('${OUT}_small.png');print('${OUT}_small.png',w,h,'window',$WX,$WY,$WW,$WH)"
