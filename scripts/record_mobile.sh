#!/bin/bash
# Record a MOBILE app: iOS Simulator (macOS + Xcode) or Android (device/emulator via adb, or scrcpy).
# usage: record_mobile.sh ios <out.mp4> <seconds>        (booted simulator: xcrun simctl boot <udid>; drive it with
#                                                         xcrun simctl openurl / ui tests / cliclick on the Simulator window)
#        record_mobile.sh android <out.mp4> <seconds>    (adb screenrecord, max 180 s per clip; or scrcpy --record if installed)
#        add --dry-run to print the command only.  Physical iPhone: QuickTime ▸ New Movie Recording ▸ select the iPhone.
set -e; P=$1; OUT=$2; SEC=$3; DRY=0; [[ " $* " == *" --dry-run "* ]] && DRY=1
# no eval: every command runs with its arguments passed as an array (filenames with spaces/quotes/; are safe)
show(){ printf '%q ' "$@"; echo; }
case $P in
  ios) if [ $DRY = 1 ]; then show xcrun simctl io booted recordVideo --codec=h264 --force "$OUT"; echo "  (stopped after $SEC s with SIGINT)"
       else xcrun simctl io booted recordVideo --codec=h264 --force "$OUT" & PID=$!; sleep "$SEC"; kill -INT "$PID"; wait "$PID" || true; fi;;
  android) if command -v scrcpy >/dev/null; then
             if [ $DRY = 1 ]; then show timeout "$SEC" scrcpy --no-playback "--record=$OUT"; else timeout "$SEC" scrcpy --no-playback "--record=$OUT" || true; fi
           else
             if [ $DRY = 1 ]; then show adb shell screenrecord --time-limit "$SEC" --bit-rate 12000000 /sdcard/demo_rec.mp4; show adb pull /sdcard/demo_rec.mp4 "$OUT"
             else adb shell screenrecord --time-limit "$SEC" --bit-rate 12000000 /sdcard/demo_rec.mp4 && adb pull /sdcard/demo_rec.mp4 "$OUT" && adb shell rm /sdcard/demo_rec.mp4; fi
           fi;;
  *) echo "platform must be ios or android" >&2; exit 1;;
esac
[ $DRY = 1 ] || echo "recorded $OUT"
