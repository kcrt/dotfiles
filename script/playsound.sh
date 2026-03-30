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
    afplay "$FILE"
elif command -v paplay &>/dev/null; then
    paplay "$FILE"
elif command -v aplay &>/dev/null; then
    aplay "$FILE" 2>/dev/null
elif command -v mpv &>/dev/null; then
    mpv --no-video --really-quiet "$FILE"
else
    # No audio player available — exit silently (don't break hooks)
    exit 0
fi
