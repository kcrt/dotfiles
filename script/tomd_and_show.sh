#!/bin/bash

# script/tomd_and_show.sh
# Usage: ./tomd_and_show.sh <input_file>
# Description: Converts a file to Markdown using tomd.sh and displays it with glow or bat.

# Check if an input file argument is provided
if [ -z "$1" ]; then
    echo "Usage: $(basename "$0") <input_file>" >&2
    exit 1
fi

input_file="$1"
# Determine the absolute path to the script directory
# This ensures that tomd.sh can be found reliably
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
tomd_script_path="$script_dir/tomd.sh"

# Check if the input file exists
if [ ! -f "$input_file" ]; then
    echo "Error: Input file '$input_file' not found." >&2
    exit 1
fi

# Convert the file to Markdown using tomd.sh
# Capture stdout and stderr separately to check for tomd.sh errors
# However, tomd.sh already prints errors to stderr and exits.
# We just need to capture its stdout for the markdown content.
converted_markdown=$("$tomd_script_path" "$input_file")
conversion_exit_code=$?

if [ $conversion_exit_code -ne 0 ]; then
    # tomd.sh should have already printed an error message to stderr.
    # We echo a general error here as well.
    echo "Error: Conversion process failed with exit code $conversion_exit_code." >&2
    exit $conversion_exit_code
fi

# Display the Markdown output
if command -v glow &> /dev/null; then
    echo "$converted_markdown" | glow -p
elif command -v bat &> /dev/null; then
    # Use --language md for syntax highlighting and --paging=never for non-interactive use
    echo "$converted_markdown" | bat --language md --paging=never
else
    echo "Warning: Neither 'glow' nor 'bat' command found. Displaying raw Markdown." >&2
    echo "$converted_markdown"
fi

exit 0
