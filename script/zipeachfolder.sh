#!/bin/sh


# zip each folder in the current directory parallelly
# usage: zipeachfolder.sh [--help]

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: zipeachfolder.sh [--help]"
    echo ""
    echo "Zip each folder in the current directory in parallel."
    echo "Creates a .zip file for each subdirectory found."
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message and exit"
    echo ""
    echo "Example:"
    echo "  zipeachfolder.sh"
    exit 0
fi

find . -maxdepth 1 -type d -print | grep -v "^.$" | parallel --unsafe --progress --bar zip -q -r {}.zip {}
