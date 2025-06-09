#!/bin/bash

#===============================================================================
#
#          FILE:  tomd.sh
#
#         USAGE:  ./tomd.sh <input_file>
#
#   DESCRIPTION:  Converts a given file (e.g., PDF, DOCX) to Markdown.
#                 It primarily uses the 'pandoc' utility.
#
#       OPTIONS:  ---
#  REQUIREMENTS:  pandoc
#          BUGS:  ---
#         NOTES:  Conversion quality depends on pandoc's capabilities for each format.
#        AUTHOR:  kcrt <kcrt@kcrt.net> (adapted by Cline)
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

# Check if pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo "Error: pandoc command not found. Please install it (e.g., sudo apt-get install pandoc or brew install pandoc)." >&2
    exit 1
fi

# Get the file extension
file_extension="${input_file##*.}"
file_extension_lower=$(echo "$file_extension" | tr '[:upper:]' '[:lower:]')

# Convert based on file type
case "$file_extension_lower" in
    pdf|rtf|doc|docx|odt|epub|mdoc|html|htm)
        echo "Info: Attempting conversion to Markdown with pandoc for .$file_extension_lower" >&2
        pandoc "$input_file" -t markdown --wrap=none
        ;;
    *)
        echo "Error: Unsupported file type '$file_extension_lower' for Markdown conversion with this script." >&2
        echo "You might be able to convert it if pandoc supports the format directly." >&2
        exit 1
        ;;
esac

exit 0
