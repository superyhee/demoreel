#!/bin/bash
# Shared macOS helpers — source it:  . "$(dirname "$0")/mac_lib.sh"
# App/window names are passed to AppleScript as argv (never spliced into the script source) so quotes in names can't inject code.
front(){ osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true'; }
win_title(){ osascript -e 'on run argv' -e 'tell application "System Events" to tell process (item 1 of argv) to get name of front window' -e 'end run' "$1" 2>/dev/null; }
# ready <app> <title-substr|->: frontmost app is <app> and (unless '-') its front window title contains <title-substr>
ready(){ [ "$(front)" = "$1" ] || return 1; [ "$2" = "-" ] && return 0; [[ "$(win_title "$1")" == *"$2"* ]]; }
# secure <app> <title-substr|->: activate <app> up to 4 times until ready
secure(){ for _ in 1 2 3 4; do osascript -e 'on run argv' -e 'tell application (item 1 of argv) to activate' -e 'end run' "$1" >/dev/null 2>&1; sleep 0.8; ready "$1" "$2" && return 0; done; return 1; }
# swift_bin <name> < source.swift: compile once into ~/.cache/demoreel/<name> (needs Xcode CLT), print the binary path
swift_bin(){ local bin="$HOME/.cache/demoreel/$1" src
  if [ -x "$bin" ]; then cat >/dev/null; else mkdir -p "${bin%/*}"; src=$(mktemp -d)/"$1".swift; cat > "$src"; swiftc -O "$src" -o "$bin" >&2 || return 1; fi
  echo "$bin"; }
