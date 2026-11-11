#!/bin/bash
# Real mouse-wheel scroll at a screen point (macOS). Keyboard scrolling (Home/End/PageDown) does NOT reach nested
# overflow:auto panes in Electron/web UIs (chat transcripts, feeds) — a wheel event at the pane does.
# usage: scroll_mac.sh <x> <y> <notches> <up|down>      (logical points, same coords as cliclick)
# Compiles a tiny Swift helper once into ~/.cache/demoreel/qscroll (needs Xcode command-line tools: xcode-select --install).
set -euo pipefail
[ $# -eq 4 ] || { echo "usage: $0 x y notches up|down" >&2; exit 2; }
X=$1; Y=$2; N=$3; case "$4" in up) D=10;; down) D=-10;; *) echo "direction must be up|down" >&2; exit 2;; esac
BIN="$HOME/.cache/demoreel/qscroll"
if [ ! -x "$BIN" ]; then
  mkdir -p "$(dirname "$BIN")"; SRC=$(mktemp -d)/qscroll.swift
  cat > "$SRC" <<'SWIFT'
import Foundation
import CoreGraphics
let a = CommandLine.arguments
let x = Double(a[1])!, y = Double(a[2])!, n = Int(a[3])!, d = Int32(a[4])!
CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: CGPoint(x: x, y: y), mouseButton: .left)?.post(tap: .cghidEventTap)
for _ in 0..<n { CGEvent(scrollWheelEvent2Source: nil, units: .line, wheelCount: 1, wheel1: d, wheel2: 0, wheel3: 0)?.post(tap: .cghidEventTap); usleep(15000) }
SWIFT
  swiftc -O "$SRC" -o "$BIN"
fi
"$BIN" "$X" "$Y" "$N" "$D"
