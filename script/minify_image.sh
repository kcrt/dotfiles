#!/usr/bin/env zsh
#
# usage: ./minify_image.sh <image_file>
#
# This script uses ImageMagick to minify the given image file.
# The minified image file will be overwritten.
#

if [ $# -ne 1 ]; then
    echo "Usage: $0 <image_file>"
    exit 1
fi

TARGET_FILE=$1

# Check if the image file is smaller in size after minification
# usage: is_shrinked <original_file> <minified_file>
function is_shrinked() {
    original_size=`wc -c < "$1"`
    minified_size=`wc -c < "$2"`
    if [ $minified_size -lt $original_size ]; then
        return 0
    else
        return 1
    fi
}

# Acquire width, height, filesize of the image file
width=`identify -format "%w" $TARGET_FILE`
height=`identify -format "%h" $TARGET_FILE`
pixel_count=`echo "$width * $height" | bc`
filesize=`wc -c < "$TARGET_FILE"`

# if file is .png, convert to .jpg
if [ "${TARGET_FILE:e:l}" = "png" ]; then
    convert "$TARGET_FILE" "${TARGET_FILE:r}.jpg"
    if is_shrinked $TARGET_FILE "${TARGET_FILE:r}.jpg"; then
        rm $1
        TARGET_FILE="${TARGET_FILE:r}.jpg"
    else
        rm "${1:r}.jpg"
    fi
fi

# ignore image le 1.5MB
if [ $filesize -gt 1500000 ]; then
    convert $TARGET_FILE -resize "3500x3500>" -quality 85 ${TARGET_FILE:r}_minified.jpg
    if is_shrinked $TARGET_FILE "${TARGET_FILE:r}_minified.jpg"; then
        rm $TARGET_FILE
        mv "${TARGET_FILE:r}_minified.jpg" $TARGET_FILE
    else
        rm "${TARGET_FILE:r}_minified.jpg"
    fi
fi

min_filesize=`wc -c < "$TARGET_FILE"`

if [ "$VERBOSE" = "1" ]; then
    echo "${TARGET_FILE}: $filesize -> $min_filesize (`echo "scale=2; $min_filesize / $filesize * 100" | bc`%)"
fi
