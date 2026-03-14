#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Rendering NifraimMarketing (MP4, h264, crf 18)..."
npx remotion render NifraimMarketing out/nifraim-marketing.mp4 \
  --codec h264 \
  --crf 18 \
  --color-space bt709

echo "Extracting poster still (frame 160)..."
npx remotion still NifraimMarketing out/nifraim-marketing-poster.png \
  --frame 160

echo "Done!"
echo "  Video: out/nifraim-marketing.mp4"
echo "  Poster: out/nifraim-marketing-poster.png"
