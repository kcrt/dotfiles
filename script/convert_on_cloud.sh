#!/usr/bin/env zsh

if [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ $# -eq 0 ]; then
    echo "Usage: $(basename "$0") <input_video_file>"
    echo "Converts the input video file using ffmpeg running in a Docker container on a GCP VM ('krypton')."
    echo "The output is resized to 1440x810, H.264 video, AAC audio (128k)."
    echo "The converted file is saved in a 'converted' subdirectory with the same name as the input."
    exit 0
fi

echo "converting $1..."

if [ -d converted ]; then
	# do nothing
else
	mkdir converted
fi

if [ -f ts_progress_in.mp4 ]; then
	rm ts_progress_in.mp4
fi
if [ -f ts_progress_out.mp4 ]; then
	rm ts_progress_out.mp4
fi

ffmpeg -i "$1" -vcodec copy -acodec copy -f mpegts ts_progress_in.mp4
cat ts_progress_in.mp4 |  gcloud compute ssh krypton --command="docker run -i --rm jrottenberg/ffmpeg -i pipe:0 -s 1440x810 -vsync passthrough -vcodec libx264 -acodec aac -ac 2 -ab 128k -threads 0 -f mpegts pipe:1" > ts_progress_out.mp4
ffmpeg -i ts_progress_out.mp4 -vcodec copy -acodec copy converted/$1

rm ts_progress_in.mp4
rm ts_progress_out.mp4
