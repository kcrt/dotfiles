#!/bin/sh

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Reads text from the macOS clipboard, converts it from UTF-8-MAC (NFD) to standard UTF-8 (NFC),"
    echo "and copies the result back to the clipboard."
    echo "Requires pbpaste, pbcopy, and iconv (standard macOS utilities)."
    exit 0
fi

pbpaste | iconv -f utf-8-mac -t utf-8 | pbcopy
