#!/bin/sh

#===============================================================================
#
#          FILE:  trash.sh
#
#         USAGE:  ./trash.sh _FILE1_ _FILE2_ _DIR1_ ...
#
#   DESCRIPTION:  Move files (or dirs) to trash, instead of rm.
#                 If the file is in an other volume, ask the user before moving
#                 them to trash.
#                 If the file with same name is already in trash, add a datetime
#                 suffix to the name.
#
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

TRASH_DIR="$HOME/.Trash"

if [ ! -d "$TRASH_DIR" ]; then
    mkdir "$TRASH_DIR"
    echo "Created trash directory: $TRASH_DIR"
fi

TRASH_FILESYSTEM=$(df -P "$TRASH_DIR" | tail -n 1 | awk '{print $1}')
# Move files (or dirs) to trash
for file in "$@"; do

    # Check if the file exists
    if [ ! -e "$file" ]; then
        echo "⚠️  File $file does not exist!"
        continue
    fi

    # Check if the file is in an other volume
    # If so, ask the user before moving them to trash
    TARGET_FILESYSTEM=$(df "$file" | tail -n 1 | awk '{print $1}')
    if [ "$TARGET_FILESYSTEM" != "$TRASH_FILESYSTEM" ]; then
        echo "The file $file is located in $TARGET_FILESYSTEM."
        echo "Are you sure you want to move it to trash in $TRASH_FILESYSTEM ? (y/N)"
        read answer
        # Abort if the answer is not "y" nor "Y"
        if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
            # skip this file
            continue
        fi
    fi

    # Check if the file is already in trash
    # If file exists, add a datetime suffix to the file name
    if [ -e "$TRASH_DIR/$file" ]; then
        # acquire filename from $file (could be a path)
        filename=$(basename "$file")
        mv "$file" "$TRASH_DIR/$filename-$(date +%Y-%m-%d-%H-%M-%S)"
    else
        mv "$file" "$TRASH_DIR"
    fi

    echo "Moved '$file' into trash🗑!"
done

