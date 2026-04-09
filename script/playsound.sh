#!/bin/bash
# Cross-platform audio playback wrapper
# Usage: playsound.sh <audio_file>
# Exits successfully even if no audio player is available (safe for hooks)

[[ $# -eq 1 ]] || { echo "Usage: $0 <audio_file>" >&2; exit 1; }

FILE="$1"
# Expand ~ in path
FILE="${FILE/#\~/$HOME}"

[[ -f "$FILE" ]] || { echo "Error: $FILE not found" >&2; exit 1; }

if command -v afplay &>/dev/null; then
    nohup afplay "$FILE" &>/dev/null &
elif command -v paplay &>/dev/null; then
    nohup paplay "$FILE" &>/dev/null &
elif command -v aplay &>/dev/null; then
    nohup aplay "$FILE" &>/dev/null &
elif command -v mpv &>/dev/null; then
    nohup mpv --no-video --really-quiet "$FILE" &>/dev/null &
else
    # No audio player available — exit silently (don't break hooks)
    exit 0
fi

# Detach background process so the script can exit immediately
disown 2>/dev/null
exit 0
