#!/usr/bin/env zsh

# Usage: whisper-cpp-jp.sh input.m4a

if [ $# -ne 1 ]; then
  echo "Usage: whisper-cpp-jp.sh input.m4a"
  exit 1
fi
FILENAME=$1

ffmpeg -i "$FILENAME" -ar 16000 -f wav /tmp/WHISPER_CPP_JP_TMP.wav
GGML_METAL_PATH_RESOURCES=~/bin/whisper-cpp-lib/ ~/bin/whisper-cli \
  -m ~/bin/whisper-cpp-lib/ggml-large-v3-q5_0.bin \
  -l ja --output-vtt \
  --print-progress \
  -f /tmp/WHISPER_CPP_JP_TMP.wav
mv /tmp/WHISPER_CPP_JP_TMP.wav.vtt "${FILENAME:r}.txt"
rm /tmp/WHISPER_CPP_JP_TMP.wav
