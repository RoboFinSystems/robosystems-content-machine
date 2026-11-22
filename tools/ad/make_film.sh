#!/bin/sh
# Build one film end to end from its spec. Run from the content machine's root:
#   just ad-film <name>          (spec: tools/ad/films/<name>.json; output: showcase/robosystems_ad/films/<name>/)
# Needs Blender (brew install --cask blender) and the renderer set up (just render-setup).
# Steps: voice + timeline (the film kit, tools/film/), the Blender plates its scenes need, the type layer,
# the assembly (the kit's), a pop scan.
set -e
NAME=$1
AD=tools/ad
F=showcase/robosystems_ad/films/$NAME
BL=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
UV_ENV_FILE=.env uv run --with faster-whisper --with 'av<16' --with librosa --with soundfile python $AD/film.py $AD/films/$NAME.json
mkdir -p $F/plates $F/renders
has() { python3 -c "import json,sys;sys.exit(0 if any(s['name']=='$1' for s in json.load(open('$F/timeline.json'))['scenes']) else 1)"; }
plate() { # shot, script, extra args
  rm -rf $F/plates/$1
  $BL -b -P $AD/blender/$2 -- "$PWD/$F/plates/$1" --film "$PWD/$F" $3 >/dev/null 2>&1
  ffmpeg -v error -y -framerate 30 -start_number 1 -i $F/plates/$1/frame-%04d.png -c:v libx264 -pix_fmt yuv420p -crf 14 -movflags +faststart $F/plates/$1.mp4
  [ -f $F/plates/$1/anchors.json ] && cp $F/plates/$1/anchors.json $F/anchors_$1.json
  echo "  plate $1: $(ls $F/plates/$1 | grep -c frame-) frames"
}
if has reveal; then plate graph_hero graph_hero.py "--samples 32"; fi
if has trace; then plate trace shots.py "--shot trace"; fi
if has share; then plate share shots.py "--shot share"; fi
SIZE=$(python3 -c "import json;print('1080 1920' if json.load(open('$F/timeline.json'))['format']=='tall' else '1920 1080')")
set -- $SIZE
node renderer/src/cli.mjs motion --root renderer/templates --html renderer/templates/ad.html --query "film=$NAME" --width $1 --height $2 \
  --mount "/ds/=design-system,/node_modules/=renderer/node_modules,/films/=showcase/robosystems_ad/films" --name layer --out $F/renders | tail -1
python3 tools/film/assemble.py $F
uv run --with numpy python tools/motion/qa/pop-scan.py $F/renders/$NAME.mp4 --sheet none \
  --cuts "$(python3 -c "import json;print(','.join(str(s['start']) for s in json.load(open('$F/timeline.json'))['scenes'][1:]))")" | tail -12
