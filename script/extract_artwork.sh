#!/bin/bash

# Extracts the artwork from the given file and saves it to the given output file.
# ffmpeg -i <INPUT_FILE> -an -vcodec copy <OUTPUT_FILE>

# Check if the input file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <INPUT_FILE>"
    exit 1
fi

INPUT_FILE=$1
OUTPUT_FILE="${INPUT_FILE%.*}.jpg"

# Extract the artwork
ffmpeg -i "$INPUT_FILE" -an -vcodec copy "$OUTPUT_FILE"