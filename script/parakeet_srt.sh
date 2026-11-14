#!/usr/bin/env bash

#===============================================================================
#
#          FILE:  parakeet_srt.sh
#         USAGE:  ./parakeet_srt.sh [-l ja|en] <input audio> <output.srt>
#   DESCRIPTION:  Transcribe one recording with parakeet-mlx into an SRT file.
#                 Reads the input, writes only <output.srt>.
#  REQUIREMENTS:  uv
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

set -euo pipefail

readonly MODEL_JA=mlx-community/parakeet-tdt_ctc-0.6b-ja
readonly MODEL_EN=mlx-community/parakeet-tdt-0.6b-v2
# parakeet's default 120 s chunks (15 s overlap) drop whole stretches of speech:
# on a 61-minute recorder MP3 (0.7.0, 2026-11-13) they left 14 gaps totalling
# 755 s and 14,059 characters, where 20 s / 5 s left no gap and 18,203.
readonly CHUNK_SECONDS=20
readonly OVERLAP_SECONDS=5

usage(){
    echo "Usage: ${0##*/} [-l ja|en] <input audio> <output.srt>"
    echo "Transcribe the input with parakeet-mlx (${CHUNK_SECONDS} s chunks, ${OVERLAP_SECONDS} s overlap) and write SRT."
    echo "  -l ja  ${MODEL_JA} (default)"
    echo "  -l en  ${MODEL_EN}"
    echo "Normalize quiet recordings first (loudnorm_wav.sh); they lose speech otherwise."
    echo "rich draws the progress bar only on a terminal; set TTY_COMPATIBLE=1 to"
    echo "draw it into a pipe as well (maintain.sh does)."
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi

lang=ja
while getopts ":l:" opt; do
    case "$opt" in
        l) lang="$OPTARG" ;;
        *) usage >&2; exit 1 ;;
    esac
done
shift $((OPTIND - 1))
if [[ $# -ne 2 ]]; then
    usage >&2
    exit 1
fi
case "$lang" in
    ja) model="$MODEL_JA" ;;
    en) model="$MODEL_EN" ;;
    *) echo "${0##*/}: unknown language: $lang (ja / en)" >&2; exit 1 ;;
esac

readonly SRC="$1"
readonly DEST="$2"

# parakeet names its output after a template inside a directory, so write it
# into a scratch directory and move it to the exact path asked for.
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

# Not the parakeet-mlx on PATH (an old pinned `uv tool install`): v0.3.1 dropped
# everything after the first sentence even on short recordings, where 0.7.0
# keeps all of it (2026-11-13). `uv tool run` follows the latest release.
uv tool run parakeet-mlx --model "$model" \
    --chunk-duration "$CHUNK_SECONDS" --overlap-duration "$OVERLAP_SECONDS" \
    --output-format srt --output-dir "$work_dir" --output-template transcript \
    "$SRC"

# parakeet reports a failed file but still exits 0, so the missing output is
# the only sign of it. An empty file is fine: a silent recording has no text.
if [[ ! -e "$work_dir/transcript.srt" ]]; then
    echo "${0##*/}: parakeet wrote no transcript for $SRC" >&2
    exit 1
fi
mv "$work_dir/transcript.srt" "$DEST"
