#!/bin/sh

#===============================================================================
#
#          FILE:  say-wrapper.sh
#
#         USAGE:  ./say-wrapper.sh <lang> <text>
#
#   DESCRIPTION:  Wrapper for TTS commands (macOS say, Linux espeak)
#
#       OPTIONS:  ---
#  REQUIREMENTS:  macOS 'say' or Linux 'espeak'/'espeak-ng'
#          BUGS:  ---
#         NOTES:  ---
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#      REVISION:  ---
#
#===============================================================================

set -e

# Detect OS and available TTS command
if command -v say >/dev/null 2>&1; then
    TTS_CMD="say"
    PLATFORM="macos"
elif command -v espeak >/dev/null 2>&1; then
    TTS_CMD="espeak"
    PLATFORM="linux"
elif command -v espeak-ng >/dev/null 2>&1; then
    TTS_CMD="espeak-ng"
    PLATFORM="linux"
else
    echo "Error: No TTS command found. Please install 'say' (macOS) or 'espeak' (Linux)." >&2
    exit 1
fi

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <lang> <text>" >&2
    echo "Example: $0 en \"Hello World\"" >&2
    echo "Supported languages: en/us, uk, ja, ch" >&2
    echo "Detected platform: $PLATFORM" >&2
    exit 1
fi

lang="$1"
shift
text="$*"

# Speak the text based on platform
if [ "$PLATFORM" = "macos" ]; then
    # Map language codes to macOS voices
    case "$lang" in
        en|us)
            voice="Ava (Premium)"
            ;;
        uk)
            voice="Daniel"
            ;;
        ja)
            voice="Kyoko (Enhanced)"
            ;;
        ch)
            voice="Tingting"
            ;;
        *)
            echo "Unsupported language: $lang" >&2
            echo "Supported languages: en/us, uk, ja, ch" >&2
            exit 1
            ;;
    esac
    say -v "$voice" "$text"
else
    # Map language codes to espeak voices
    case "$lang" in
        en|us)
            voice="en-us"
            ;;
        uk)
            voice="en-gb"
            ;;
        ja)
            voice="ja"
            ;;
        ch)
            voice="cmn"
            ;;
        *)
            echo "Unsupported language: $lang" >&2
            echo "Supported languages: en/us, uk, ja, ch" >&2
            exit 1
            ;;
    esac
    $TTS_CMD -v "$voice" "$text"
fi
