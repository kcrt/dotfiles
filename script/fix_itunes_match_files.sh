#!/bin/bash

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Cleans and fixes M4A files to use for iTunes Match."
    echo "It creates a 'iTunes_Match_Fixed_Clean' directory and processes each .m4a file in the current directory."
    echo "The script uses ffmpeg to copy the audio stream, remove chapters and extraneous metadata, which causes rejection by iTunes Match."
    exit 0
fi

source "$(dirname "$0")/echo_color.sh"

mkdir -p "iTunes_Match_Fixed_Clean"

for file in *.m4a; do
    [[ ! -f "$file" ]] && continue
    
    # echo_aqua "Processing: $file"
    output="iTunes_Match_Fixed_Clean/${file%.*}_clean.m4a"
    
    ffmpeg -loglevel error -i "$file" \
        -c:a copy \
        -map 0:a:0 \
        -map_chapters -1 \
        -map_metadata 0:g \
        -avoid_negative_ts make_zero \
        -y "$output"
    
    if [ $? -eq 0 ]; then
        echo_green "✓ Successfully processed: $file"
    else
        echo_red "✗ Failed to process: $file"
    fi
done
