#!/bin/bash
# Record a MOBILE app: iOS Simulator (macOS + Xcode) or Android (device/emulator via adb, or scrcpy).
# usage: record_mobile.sh ios <out.mp4> <seconds>        (booted simulator: xcrun simctl boot <udid>; drive it with
#                                                         xcrun simctl openurl / ui tests / cliclick on the Simulator window)
#        record_mobile.sh android <out.mp4> <seconds>    (adb screenrecord, max 180 s per clip; or scrcpy --record if installed)
#        add --dry-run to print the command only.  Physical iPhone: QuickTime ▸ New Movie Recording ▸ select the iPhone.
set -e; P=$1; OUT=$2; SEC=$3; DRY=0; [[ " $* " == *" --dry-run "* ]] && DRY=1
run(){ if [ $DRY = 1 ]; then echo "$*"; else eval "$*"; fi; }
case $P in
  ios) run "xcrun simctl io booted recordVideo --codec=h264 --force '$OUT' & PID=\$!; sleep $SEC; kill -INT \$PID; wait \$PID";;
  android) if command -v scrcpy >/dev/null; then run "timeout $SEC scrcpy --no-playback --record='$OUT' || true"
           else run "adb shell screenrecord --time-limit $SEC --bit-rate 12000000 /sdcard/demo_rec.mp4 && adb pull /sdcard/demo_rec.mp4 '$OUT' && adb shell rm /sdcard/demo_rec.mp4"; fi;;
  *) echo "platform must be ios or android" >&2; exit 1;;
esac
[ $DRY = 1 ] || echo "recorded $OUT"
