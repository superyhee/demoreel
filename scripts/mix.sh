#!/bin/bash
# Final encode: frames + VO + music (auto-ducked under VO) + SFX, loudness-normalized to -16 LUFS.
# env: MUSIC_GAIN (default 0.42; use ~0.15 for music_pro.py which is mastered loud), SFX_GAIN (0.55)
# usage: mix.sh <frames_dir | video.mp4 from render_parallel.py> <vo.wav|-> <music.wav|-> <sfx.wav|-> <out.mp4> [fps=30] [duration=30]
set -euo pipefail
[ $# -ge 5 ] || { sed -n 4p "$0" >&2; exit 2; }
FR=$1; VO=$2; MU=$3; SF=$4; OUT=$5; FPS=${6:-30}; DUR=${7:-30}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
# loudnorm turns pure digital silence into NaN (aac then fails) → only normalize when at least one real track is given
NORM=loudnorm=I=-16:TP=-1.5:LRA=11; [ "$VO$MU$SF" = "---" ] && NORM=anull
silence(){ ffmpeg -v error -y -f lavfi -i anullsrc=r=44100:cl=stereo -t "$DUR" "$1"; }
[ "$VO" = "-" ] && { silence "$T/vo.wav"; VO=$T/vo.wav; }
[ "$MU" = "-" ] && { silence "$T/mu.wav"; MU=$T/mu.wav; }
[ "$SF" = "-" ] && { silence "$T/sf.wav"; SF=$T/sf.wav; }
for f in "$VO" "$MU" "$SF"; do [ -f "$f" ] || { echo "ERROR: missing audio input: $f" >&2; exit 1; }; done
if [ -f "$FR" ]; then VIN=(-i "$FR"); VC=(-c:v copy)
elif [ -d "$FR" ]; then VIN=(-framerate "$FPS" -i "$FR/f%04d.png"); VC=(-c:v libx264 -pix_fmt yuv420p -crf 17 -preset slow)
else echo "ERROR: video input not found: $FR" >&2; exit 1; fi
ffmpeg -v error -y "${VIN[@]}" -i "$VO" -i "$MU" -i "$SF" -filter_complex \
 "[1]volume=1.6,asplit[v1][v2];[2]volume=${MUSIC_GAIN:-0.42},equalizer=f=2500:t=q:w=1.2:g=-4[m];[v2]atrim=start=0.15,asetpts=PTS-STARTPTS,apad[v2a];[m][v2a]sidechaincompress=threshold=0.015:ratio=10:attack=8:release=450:knee=4[md];[3]volume=${SFX_GAIN:-0.55},highpass=f=60[s];[v1][md][s]amix=inputs=3:normalize=0,${NORM}[a]" \
 -map 0:v -map "[a]" "${VC[@]}" -c:a aac -b:a 192k -t "$DUR" -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
ffmpeg -hide_banner -i "$OUT" -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume" || true
