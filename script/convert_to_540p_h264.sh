#!/usr/bin/env zsh

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Converts all video files in the current directory to 960x540 resolution,"
    echo "H.264 video codec, and AAC audio (2 channels, 128k bitrate)."
    echo "Output files are placed in a 'mini' subdirectory."
    echo "Requires ffmpeg."
    exit 0
fi

mkdir mini
for i in *; do
	if [ -f "$i" ]; then
		echo "converting $i..."
		nice ffmpeg -i "$i" -s 960x540 -vcodec libx264 -acodec aac -ac 2 -ab 128k "mini/$i"
	fi
done
