#!/bin/bash
# Computer-use guard for desktop recordings (macOS). Clicks ONLY if <app> is frontmost AND its front window title contains
# <title-substr>; logs "<t> <label>" relative to $REC_T0_FILE (epoch seconds written when recording started).
# usage: guarded_act.sh <app> <title-substr> <label> [cliclick args...]     e.g. guarded_act.sh MyApp my-demo "click Save" c:1107,457
set -uo pipefail
[ $# -ge 3 ] || { sed -n 4p "$0" >&2; exit 2; }
APP=$1; TS=$2; LABEL=$3; shift 3
# values are passed as argv (never spliced into AppleScript/Python source) so quotes in names can't inject code
. "$(dirname "$0")/mac_lib.sh"
ready "$APP" "$TS" || { echo "ABORT: frontmost=$(front) window=$(win_title "$APP")"; exit 1; }
T0=${REC_T0_FILE:-/tmp/rec_t0}
T=$( [ -f "$T0" ] && python3 -c 'import sys,time;print(round(time.time()-float(open(sys.argv[1]).read()),2))' "$T0" || echo NA)
echo "$T $LABEL" >> "${ACT_LOG:-/tmp/actions.log}"; [ $# -gt 0 ] && cliclick -e 250 "$@"; echo "t=$T ok"
