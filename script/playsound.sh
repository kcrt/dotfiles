#!/bin/bash
# Cross-platform audio playback wrapper
# Usage: playsound.sh <audio_file>
# Exits successfully even if no audio player is available (safe for hooks)

# If the audio daemon (e.g. coreaudiod) stalls, players never exit while hooks
# keep spawning new ones, which makes the stall worse. Guard against both.
MAX_CONCURRENT_PLAYERS=4
PLAYBACK_TIMEOUT_SECONDS=10

[[ $# -eq 1 ]] || { echo "Usage: $0 <audio_file>" >&2; exit 1; }

FILE="$1"
# Expand ~ in path
FILE="${FILE/#\~/$HOME}"

[[ -f "$FILE" ]] || { echo "Error: $FILE not found" >&2; exit 1; }

# Run the player in the background; skip if too many players are already
# running, and kill it if it has not finished within the timeout.
play_detached() {
    local player="$1"
    local running_count
    running_count=$(pgrep -x "$player" | wc -l)
    (( running_count >= MAX_CONCURRENT_PLAYERS )) && return 0

    nohup bash -c '
        "$@" &
        player_pid=$!
        ( sleep "$TIMEOUT"; kill -9 "$player_pid" 2>/dev/null ) &
        watchdog_pid=$!
        wait "$player_pid"
        kill "$watchdog_pid" 2>/dev/null
    ' playsound "$@" &>/dev/null &
}
export TIMEOUT="$PLAYBACK_TIMEOUT_SECONDS"

if command -v afplay &>/dev/null; then
    play_detached afplay "$FILE"
elif command -v paplay &>/dev/null; then
    play_detached paplay "$FILE"
elif command -v aplay &>/dev/null; then
    play_detached aplay "$FILE"
elif command -v mpv &>/dev/null; then
    play_detached mpv --no-video --really-quiet "$FILE"
else
    # No audio player available — exit silently (don't break hooks)
    exit 0
fi

# Detach background process so the script can exit immediately
disown 2>/dev/null
exit 0
