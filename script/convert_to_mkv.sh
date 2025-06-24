#!/bin/zsh

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0") <input_video_file>"
    echo "Converts the input video file to an MKV container using HandBrakeCLI."
    echo "Uses the 'H.264 MKV 720p30' preset."
    echo "Output is saved to /Volumes/Media/mkv/input_video_file.mkv (if /Volumes/Media/mkv exists)."
    echo "Requires HandBrakeCLI."
    exit 0
fi

if [ -z "$1" ]; then
    echo "Error: Input video file not specified."
    echo "Usage: $(basename "$0") <input_video_file>"
    echo "For more help, run: $(basename "$0") --help"
    exit 1
fi

if [[ -e /Volumes/Media/mkv ]]; then
	handbrakecli -i "$1" -o "/Volumes/Media/mkv/${1:t:r}.mkv" -Z "H.264 MKV 720p30"
else
	OSError "/Volumes/Media/mkv not found."
fi
