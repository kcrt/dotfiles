#!/bin/bash
set -euo pipefail

usage() {
    echo "Usage: $0 [-s soundfont] [-o output.m4a] <file.abc>" >&2
    exit 1
}

SOUNDFONT=~/system/SoundFont/GeneralUser-GS.sf2
OUTPUT=""

while getopts "s:o:" opt; do
    case $opt in
        s) SOUNDFONT="$OPTARG" ;;
        o) OUTPUT="$OPTARG" ;;
        *) usage ;;
    esac
done
shift $((OPTIND - 1))

[[ $# -eq 1 ]] || usage
ABC_FILE="$1"

[[ -f "$ABC_FILE" ]] || { echo "Error: $ABC_FILE not found" >&2; exit 1; }
[[ -f "$SOUNDFONT" ]] || { echo "Error: soundfont $SOUNDFONT not found" >&2; exit 1; }

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

abc2midi "$ABC_FILE" -o "$TMPDIR/out.mid" > /dev/null
fluidsynth -ni -T wav -F "$TMPDIR/out.wav" -r 44100 "$SOUNDFONT" "$TMPDIR/out.mid" > /dev/null 2>&1

if [[ -n "$OUTPUT" ]]; then
    afconvert -f m4af -d aac "$TMPDIR/out.wav" "$OUTPUT"
else
    afplay "$TMPDIR/out.wav"
fi
