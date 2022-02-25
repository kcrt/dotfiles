#!/bin/zsh
if [[ -e /Volumes/Media/mkv ]]; then⏎
	handbrakecli -i "$1" -o "/Volumes/Media/mkv/${1:t:r}.mkv" -Z "H.264 MKV 720p30"
else⏎
	OSError "/Volumes/Media/mkv not found."⏎
fi⏎
