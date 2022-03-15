#!/bin/bash

# --add-metadata raise error in iTunes Match
echo "Use yt-dlp instead of youtube-dl"
yt-dlp --extract-audio --format m4a --embed-thumbnail --add-metadata --  "$1"
AtomicParsley *$1*.m4a --album "Downloaded from YouTube/Nicovideo"
