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

album_name="Downloaded from YouTube/Nicovideo"
music_auto_add_dir="$HOME/Music/Music/Media.localized/Automatically Add to Music.localized"

# yt-dlp writes the final path of each downloaded file here (one per line)
downloaded_list=$(mktemp)
trap 'rm -f "$downloaded_list"' EXIT

echo "Use yt-dlp instead of youtube-dl"
yt-dlp --extract-audio --format m4a --embed-thumbnail \
    --print-to-file after_move:filepath "$downloaded_list" \
    -- "$1" || exit 1

if [ ! -s "$downloaded_list" ]; then
    echo "Error: no file was downloaded" >&2
    exit 1
fi

while IFS= read -r file; do
    AtomicParsley "$file" \
        --album "$album_name" \
        --albumArtist "$album_name" \
        --overWrite
done < "$downloaded_list"

read -r -p "Add to Music? (Y/n) " answer
case "$answer" in
    [nN]*) exit 0 ;;
esac

if [ ! -d "$music_auto_add_dir" ]; then
    echo "Error: $music_auto_add_dir not found" >&2
    exit 1
fi

while IFS= read -r file; do
    cp -- "$file" "$music_auto_add_dir/" && echo "Added to Music: $(basename "$file")"
done < "$downloaded_list"
