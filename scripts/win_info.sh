#!/bin/bash
# Print "<window-id> <x> <y> <w> <h>" (logical points, top-left origin) of an app's largest on-screen normal window (macOS).
# Used by explore_act.sh to screenshot ONLY that window (screencapture -l) — other apps' content never lands in a shot —
# and to convert window-screenshot pixels into screen click coordinates. usage: win_info.sh "<App process name>"
set -euo pipefail
[ $# -eq 1 ] || { echo "usage: $0 \"<App>\"" >&2; exit 2; }
BIN="$HOME/.cache/demoreel/qwin2"
if [ ! -x "$BIN" ]; then
  mkdir -p "$(dirname "$BIN")"; SRC=$(mktemp -d)/qwin.swift
  cat > "$SRC" <<'SWIFT'
import Foundation
import CoreGraphics
let pid = Int(CommandLine.arguments[1])!
let opts: CGWindowListOption = [.optionOnScreenOnly, .excludeDesktopElements]
let list = (CGWindowListCopyWindowInfo(opts, kCGNullWindowID) as? [[String: Any]]) ?? []
var best: (Int, Double, Double, Double, Double)? = nil
for w in list {
  guard (w[kCGWindowOwnerPID as String] as? Int) == pid, (w[kCGWindowLayer as String] as? Int) == 0,
        let b = w[kCGWindowBounds as String] as? [String: Double], let id = w[kCGWindowNumber as String] as? Int else { continue }
  let (x, y, ww, hh) = (b["X"] ?? 0, b["Y"] ?? 0, b["Width"] ?? 0, b["Height"] ?? 0)
  if ww < 200 || hh < 150 { continue }
  if best == nil || ww * hh > best!.3 * best!.4 { best = (id, x, y, ww, hh) }
}
guard let r = best else { FileHandle.standardError.write("no on-screen window for pid \(pid)\n".data(using: .utf8)!); exit(1) }
print(r.0, Int(r.1), Int(r.2), Int(r.3), Int(r.4))
SWIFT
  swiftc -O "$SRC" -o "$BIN"
fi
# match by PID: the window-server owner name can differ from the process name (e.g. bundle display name "Acme Pro" vs process name "Acme")
PID=$(osascript -e "tell application \"System Events\" to get unix id of process \"$1\"" 2>/dev/null) || { echo "no running process \"$1\"" >&2; exit 1; }
"$BIN" "$PID"
