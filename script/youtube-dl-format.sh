#!/bin/bash

source $HOME/dotfiles/script/echo_color.sh

# if no argument is given, show help
if [ $# -eq 0 ]; then
    echo "Usage: $0 URL"
    exit 0
fi
URL=$1

echo "Use yt-dlp instead of youtube-dl"
# check if yt-dlp is installed
if [ ! -x "$(command -v yt-dlp)" ]; then
    echo_error "Error: yt-dlp is not installed." >&2
    exit 1
fi

yt-dlp --quiet -F "$URL"

echo "Which format do you want to download? "
read FORMAT

yt-dlp -f $FORMAT "$URL"
