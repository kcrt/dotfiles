#!/usr/bin/env zsh

# Usage: movie_size_per_duration.sh [at_least]
# Print the size per duration of all the movie files in the current directory.
# If at_least is specified, only print the files whose size per duration is greater than at_least.

get_file_size() {
    local file="$1"
    if [[ "$(uname)" == "Darwin" ]]; then
        stat -f%z "$file" # macOS command to get file size in bytes
    else
        stat --printf="%s" "$file" # Linux command to get file size in bytes
    fi
}

if [ $# -eq 1 ]; then
    at_least=$1
else
    at_least=0
fi

for file in **/*.{mp4,mkv}(N); do
    size=$(get_file_size "$file")
    duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file")
    size_per_second=$(echo "scale=2; $size / 1024.0 / 1024.0 / ($duration / 60)" | bc)
    if [ $(echo "$size_per_second > $at_least" | bc) -eq 0 ]; then
        continue
    fi
    echo "$size_per_second MB/min.: $file"
done