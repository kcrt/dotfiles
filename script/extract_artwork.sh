#!/bin/bash

# Extracts the artwork from the given file and saves it to the given output file.
# ffmpeg -i <INPUT_FILE> -an -vcodec copy <OUTPUT_FILE>

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0") <INPUT_FILE>"
    echo "Extracts the embedded artwork (cover art) from a media file using ffmpeg."
    echo "The artwork is saved as a JPG file with the same name as the input file (e.g., input.mp3 -> input.jpg)."
    echo "Requires ffmpeg."
    exit 0
fi

# Check if the input file is provided
if [ -z "$1" ]; then
    echo "Error: No input file specified."
    echo "Usage: $(basename "$0") <INPUT_FILE>"
    echo "For more help, run: $(basename "$0") --help"
    exit 1
fi

INPUT_FILE=$1
OUTPUT_FILE="${INPUT_FILE%.*}.jpg"

# Extract the artwork
ffmpeg -i "$INPUT_FILE" -an -vcodec copy "$OUTPUT_FILE"
