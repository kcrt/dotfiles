#!/usr/local/bin/zsh

ffmpeg -i "$1" -c:v hevc_videotoolbox -c:a aac -b:a 128k -s 1020x1080 -threads 4 "${1:r}.hevc"


