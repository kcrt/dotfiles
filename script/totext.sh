#!/bin/bash

#===============================================================================
#
#          FILE:  totext.sh
#
#         USAGE:  ./totext.sh <input_file>
#
#   DESCRIPTION:  Converts a given file (e.g., PDF) to plain text.
#                 For PDF files, it uses the 'pdftotext' utility.
#
#       OPTIONS:  ---
#  REQUIREMENTS:  pdftotext (for PDF files)
#          BUGS:  ---
#         NOTES:  ---
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#      REVISION:  $Id$
#
#===============================================================================

# Check if a file argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <input_file>"
    exit 1
fi

input_file="$1"

# Check if the file exists
if [ ! -f "$input_file" ]; then
    echo "Error: File '$input_file' not found."
    exit 1
fi

# Get the file extension
file_extension="${input_file##*.}"
file_extension_lower=$(echo "$file_extension" | tr '[:upper:]' '[:lower:]')

# Convert based on file type
case "$file_extension_lower" in
    pdf)
        if ! command -v pdftotext &> /dev/null; then
            echo "Error: pdftotext command not found. Please install it (e.g., sudo apt-get install poppler-utils or brew install poppler)." >&2
            exit 1
        fi
        pdftotext "$input_file" - # Output to stdout
        ;;
    rtf|doc|docx|odt)
        if command -v textutil &> /dev/null; then
            textutil -convert txt "$input_file" -stdout
        elif command -v pandoc &> /dev/null; then
            echo "Info: textutil not found for .$file_extension_lower, trying pandoc." >&2
            pandoc "$input_file" -t plain --wrap=none
        else
            echo "Error: Neither textutil nor pandoc found to convert .$file_extension_lower files." >&2
            exit 1
        fi
        ;;
    webarchive)
        if command -v textutil &> /dev/null; then
            textutil -convert txt "$input_file" -stdout
        else
            echo "Error: textutil command not found. textutil is required to convert .$file_extension_lower files." >&2
            echo "Pandoc does not support the .webarchive format." >&2
            exit 1
        fi
        ;;
    epub|mdoc)
        if command -v pandoc &> /dev/null; then
            echo "Info: Attempting conversion with pandoc for .$file_extension_lower" >&2
            pandoc "$input_file" -t plain --wrap=none
        else
            echo "Error: pandoc command not found. pandoc is required to convert .$file_extension_lower files." >&2
            exit 1
        fi
        ;;
    zip|lzh|rar)
        if command -v als &> /dev/null; then
            als "$input_file"
        else
            echo "Error: als command not found. als is required to list contents of archive files." >&2
            exit 1
        fi
        ;;
    *)
        echo "Error: Unsupported file type '$file_extension_lower'." >&2
        exit 1
        ;;
esac

exit 0
