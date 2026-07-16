#!/bin/bash
# Composite an avatar short: backdrop (behind) + green-keyed HeyGen avatar + overlay (front).
# The avatar mp4 must be rendered on a pure-green (#00FF00) background (see heygen_green.py).
#
# Usage: ./composite.sh BACKDROP.png AVATAR_GREEN.mp4 OVERLAY.png OUT.mp4
set -euo pipefail
BG="$1"; AV="$2"; OV="$3"; OUT="$4"

ffmpeg -y -loglevel error -loop 1 -i "$BG" -i "$AV" -loop 1 -i "$OV" -filter_complex "
[0:v]scale=720:1280,setsar=1[bg];
[1:v]chromakey=0x00FF00:0.13:0.06,despill=type=green[ky];
[bg][ky]overlay=0:0[a];
[a][2:v]overlay=0:0[out]
" -map "[out]" -map 1:a -shortest -r 30 -pix_fmt yuv420p -c:v libx264 -c:a aac "$OUT"
echo "wrote $OUT"
