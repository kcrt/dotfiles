#!/usr/bin/env bash

#===============================================================================
#
#          FILE:  loudnorm_wav.sh
#         USAGE:  ./loudnorm_wav.sh <input audio/video> <output.wav>
#   DESCRIPTION:  Two-pass loudnorm into a 16 kHz mono WAV, ready for speech
#                 recognition. Reads the input, writes only <output.wav>.
#  REQUIREMENTS:  ffmpeg, ffprobe
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

set -euo pipefail

readonly TARGET_I=-16      # integrated loudness (LUFS)
readonly TARGET_TP=-1.5    # true peak (dBTP)
readonly TARGET_LRA=11     # loudness range (LU)

usage(){
    echo "Usage: ${0##*/} <input audio/video> <output.wav>"
    echo "Measure the loudness of the input, then normalize it in a second pass to"
    echo "I=${TARGET_I} LUFS / TP=${TARGET_TP} dBTP / LRA=${TARGET_LRA} LU and write 16 kHz mono PCM."
    echo "A recording whose peaks already hit 0 dB only distorts when simply made"
    echo "louder; the measured second pass is what avoids that."
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi
if [[ $# -ne 2 ]]; then
    usage >&2
    exit 1
fi

readonly SRC="$1"
readonly DEST="$2"

# The measuring pass prints its result on stderr, so it goes to a file while
# stdout carries the progress.
ffmpeg_log="$(mktemp)"
trap 'rm -f "$ffmpeg_log"' EXIT

# Total length in microseconds, the unit of ffmpeg's out_time_us. Empty when
# ffprobe cannot tell; the progress line then shows the position alone.
total_us="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC" \
    | awk '$1 ~ /^[0-9.]+$/ { printf "%d", $1 * 1000000 }')" || total_us=""

# format_us <microseconds> -> "1:02:03" or "2:03"
format_us(){
    local -i seconds=$(( $1 / 1000000 ))
    if (( seconds >= 3600 )); then
        printf '%d:%02d:%02d' $(( seconds / 3600 )) $(( seconds % 3600 / 60 )) $(( seconds % 60 ))
    else
        printf '%d:%02d' $(( seconds / 60 )) $(( seconds % 60 ))
    fi
}

# show_progress <label> < ffmpeg -progress output
# Redraws one line with CR: an hours-long recorder file takes minutes per pass,
# and without it nothing tells a slow pass from a stuck one. The line is only
# redrawn when the percentage changes (or, with no known length, the minute),
# so the log maintain.sh keeps of it stays short.
show_progress(){
    local label=$1 key value step last_step=""
    while IFS='=' read -r key value; do
        [[ "$key" == out_time_us && "$value" =~ ^[0-9]+$ ]] || continue
        if [[ -n "$total_us" ]] && (( total_us > 0 )); then
            step=$(( value * 100 / total_us ))
            [[ "$step" == "$last_step" ]] && continue
            printf '\r[loudnorm] %s %3d%% (%s / %s)' "$label" "$step" \
                "$(format_us "$value")" "$(format_us "$total_us")" >&2
        else
            step=$(( value / 60000000 ))
            [[ "$step" == "$last_step" ]] && continue
            printf '\r[loudnorm] %s %s' "$label" "$(format_us "$value")" >&2
        fi
        last_step=$step
    done
    [[ -z "$last_step" ]] || printf '\n' >&2
}

# -vn is required: without it ffmpeg decodes the video too, which made the
# measuring pass over a 44-minute Zoom recording take minutes instead of ~20 s.
if ! ffmpeg -hide_banner -nostdin -nostats -progress pipe:1 -vn -i "$SRC" \
        -af "loudnorm=I=${TARGET_I}:TP=${TARGET_TP}:LRA=${TARGET_LRA}:print_format=json" \
        -f null - 2>"$ffmpeg_log" | show_progress "Measuring ${SRC##*/}"; then
    # The reason is in the log, which the trap is about to delete.
    tail -n 5 "$ffmpeg_log" >&2
    echo "[loudnorm] Could not measure the loudness of $SRC" >&2
    exit 1
fi
measured="$(sed -n '/^{/,/^}/p' "$ffmpeg_log")"

extract_measured() { sed -n "s/.*\"$1\" *: *\"\([^\"]*\)\".*/\1/p" <<<"$measured"; }
in_i="$(extract_measured input_i)"
in_tp="$(extract_measured input_tp)"
in_lra="$(extract_measured input_lra)"
in_thresh="$(extract_measured input_thresh)"
offset="$(extract_measured target_offset)"
if [[ -z "$in_i" || -z "$offset" ]]; then
    echo "[loudnorm] Could not measure the loudness of $SRC" >&2
    exit 1
fi
echo "[loudnorm] Input: I=${in_i} LUFS / TP=${in_tp} dBTP / LRA=${in_lra}"

ffmpeg -hide_banner -nostdin -nostats -progress pipe:1 -loglevel error -y -vn -i "$SRC" \
    -af "loudnorm=I=${TARGET_I}:TP=${TARGET_TP}:LRA=${TARGET_LRA}:measured_I=${in_i}:measured_TP=${in_tp}:measured_LRA=${in_lra}:measured_thresh=${in_thresh}:offset=${offset}:linear=true" \
    -ac 1 -ar 16000 -c:a pcm_s16le "$DEST" | show_progress "Normalizing to 16 kHz mono"
