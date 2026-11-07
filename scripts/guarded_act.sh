#!/bin/bash
# Computer-use guard for desktop recordings (macOS). Clicks ONLY if <app> is frontmost AND its front window title contains
# <title-substr>; logs "<t> <label>" relative to $REC_T0_FILE (epoch seconds written when recording started).
# usage: guarded_act.sh <app> <title-substr> <label> [cliclick args...]     e.g. guarded_act.sh MyApp my-demo "click Save" c:1107,457
APP=$1; TS=$2; LABEL=$3; shift 3
F=$(osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true')
W=$(osascript -e "tell application \"System Events\" to tell process \"$APP\" to get name of front window" 2>/dev/null)
if [ "$F" != "$APP" ] || [[ "$W" != *"$TS"* ]]; then echo "ABORT: frontmost=$F window=$W"; exit 1; fi
T0=${REC_T0_FILE:-/tmp/rec_t0}; T=$( [ -f "$T0" ] && python3 -c "import time;print(round(time.time()-float(open('$T0').read()),2))" || echo NA)
echo "$T $LABEL" >> "${ACT_LOG:-/tmp/actions.log}"; [ $# -gt 0 ] && cliclick -e 250 "$@"; echo "t=$T ok"
