#!/bin/bash

# --add-metadata raise error in iTunes Match
if [ -z "$1" ]; then
    echo "Usage: $(basename "$0") <URL>"
    echo "Download audio from YouTube/Nicovideo as m4a"
    echo ""
    echo "Example:"
    echo "  $(basename "$0") https://www.youtube.com/watch?v=xxx"
    exit 1
fi

# Extract video ID from URL or use as-is if already an ID
video_id="$1"
if [[ "$1" =~ v=([^&]+) ]]; then
    video_id="${BASH_REMATCH[1]}"
elif [[ "$1" =~ youtu\.be/([[:alnum:]_-]+) ]]; then
    video_id="${BASH_REMATCH[1]}"
fi

echo "Use yt-dlp instead of youtube-dl"
yt-dlp --extract-audio --format m4a --embed-thumbnail -- "$1"
AtomicParsley ./*"${video_id}"*.m4a --album "Downloaded from YouTube/Nicovideo" --overWrite
