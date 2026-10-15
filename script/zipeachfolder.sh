#!/bin/sh


# zip each folder in the current directory parallelly
# usage: zipeachfolder.sh [--help]

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: zipeachfolder.sh [--help]"
    echo ""
    echo "Zip each folder in the current directory in parallel."
    echo "Creates a .zip file for each subdirectory found."
    echo "Hidden directories are skipped, existing .zip files are recreated,"
    echo "and .DS_Store files are excluded."
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message and exit"
    echo ""
    echo "Example:"
    echo "  zipeachfolder.sh"
    exit 0
fi

# --unsafe: suppress warnings when $PWD contains symbols such as （）「」・
# rm -f: zip -r would otherwise merge into an existing archive and keep stale entries
find . -mindepth 1 -maxdepth 1 -type d ! -name '.*' -print0 \
    | parallel -0 --unsafe --bar 'rm -f {}.zip && zip -q -r {}.zip {} -x "*/.DS_Store"'
