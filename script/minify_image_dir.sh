#!/usr/bin/env zsh
#
# usage: ./minify_image.sh <image_file>
#
# This script uses ImageMagick to minify the images in specified directory.
# The minified image file will be overwritten.
#

if [ $# -ne 1 ]; then
    echo "Usage: $0 <image_file_dir>"
    exit 1
fi

TARGET_DIR=$1
TARGET_DIR_SIZE=`du -sh $TARGET_DIR | cut -f1`

image_files=`find $TARGET_DIR -type f -name "*.png" -o -name "*.jpg"`

echo "Target directory: $TARGET_DIR"
echo "Number of image files: `echo $image_files | wc -w`"

echo $image_files | parallel --progress --eta --no-notice --jobs 4 $DOTFILES/script/minify_image.sh {}

# Print the size of the directory
TARGET_DIR_CURRENT_SIZE=`du -sh $TARGET_DIR | cut -f1`
echo "Directory size: $TARGET_DIR_SIZE -> $TARGET_DIR_CURRENT_SIZE"