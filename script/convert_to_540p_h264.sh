#!/usr/bin/env zsh

mkdir mini
for i in *; do
	if [ -f "$i" ]; then
		echo "converting $i..."
		nice ffmpeg -i "$i" -s 960x540 -vcodec libx264 -acodec aac -ac 2 -ab 128k "mini/$i"
	fi
done
