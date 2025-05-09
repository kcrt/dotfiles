#!/usr/bin/env zsh

# Unified script for repacking image archives with various processing options
# Usage: repack_images.sh [options] input.zip
#
# Options:
#   --avif-to-jpeg       Convert AVIF images to JPEG (quality 90)
#   --resize-half        Resize images to 50% of original size
#   --resize-max=SIZE    Resize images to maximum dimension (default: 2000)
#   --quality=VALUE      Set JPEG quality (default: 90)
#   --no-backup          Create backup of original file (with .org extension)
#   --output=FILE        Specify output filename (default: auto-generated)
#   --help               Show this help message

# Default values
RESIZE_MODE=""
MAX_SIZE=2000
QUALITY=90
CONVERT_AVIF=false
BACKUP_ORIGINAL=true
OUTPUT_FILE=""
TEMP_DIR="/tmp/REPACK_IMAGES"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --avif-to-jpeg)
            CONVERT_AVIF=true
            shift
            ;;
        --resize-half)
            RESIZE_MODE="half"
            shift
            ;;
        --resize-max=*)
            RESIZE_MODE="max"
            MAX_SIZE="${1#*=}"
            shift
            ;;
        --quality=*)
            QUALITY="${1#*=}"
            shift
            ;;
        --no-backup)
            BACKUP_ORIGINAL=false
            shift
            ;;
        --output=*)
            OUTPUT_FILE="${1#*=}"
            shift
            ;;
        --help)
            echo "Usage: repack_images.sh [options] input.zip"
            echo ""
            echo "Options:"
            echo "  --avif-to-jpeg       Convert AVIF images to JPEG (quality 90)"
            echo "  --resize-half        Resize images to 50% of original size"
            echo "  --resize-max=SIZE    Resize images to maximum dimension (default: 2000)"
            echo "  --quality=VALUE      Set JPEG quality (default: 90)"
            echo "  --backup             Create backup of original file (with .org extension)"
            echo "  --output=FILE        Specify output filename (default: auto-generated)"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            # Assume it's the input file
            INPUT_FILE="$1"
            shift
            ;;
    esac
done

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' does not exist!"
    exit 1
fi

# Clean up any existing temp directory
rm -rf "$TEMP_DIR" || echo "Starting new process..."

# Extract file information and convert to absolute path if needed
if [[ "$INPUT_FILE" != /* ]]; then
    fullname="$(pwd)/$INPUT_FILE"
else
    fullname="$INPUT_FILE"
fi
filename="${fullname:t}"
stem="${filename:r}"
filesize=$(wc -c "$fullname" | awk '{print $1}')
(( org_filesize = filesize / 1024 / 1024 ))

echo "Processing: $stem"

# Create temporary directory
mkdir -p "$TEMP_DIR"

# Unzip the input file
echo "Extracting archive..."
unzip "$fullname" -d "$TEMP_DIR"

# Enable globstar for recursive file matching
setopt GLOBSTARSHORT

# Process AVIF files if requested
if $CONVERT_AVIF; then
    echo "Converting AVIF to JPEG (quality $QUALITY)..."
    find "$TEMP_DIR" -name "*.avif" | while read i; do
        echo "  $i"
        magick convert "$i" -quality 95 "${i:r}.jpg"
        rm "$i"
    done
    echo "Converting AVIF to JPEG done."
fi

# Process PNG files (convert to JPEG)
echo "Converting PNG to JPEG..."
find "$TEMP_DIR" -name "*.png" | while read i; do
    echo "  $i"
    magick convert "$i" -quality 95 "${i:r}_png.jpg"
    rm "$i"
done
echo "Converting PNG to JPEG done."

# Process JPEG files (resize and/or set quality) in a single operation
if [[ "$RESIZE_MODE" == "half" ]]; then
    echo "Resizing images to 50% with quality $QUALITY..."
    # find "$TEMP_DIR" -name "*.jpg" | parallel --progress -j 4 "magick mogrify -resize 50% -quality $QUALITY \"{}\""
    find "$TEMP_DIR" -name "*.jpg" | while read i; do
        echo "  $i"
        magick mogrify -resize 50% -quality $QUALITY "$i"
    done
elif [[ "$RESIZE_MODE" == "max" ]]; then
    echo "Resizing images to maximum dimension ${MAX_SIZE}x${MAX_SIZE} with quality $QUALITY..."
    # find "$TEMP_DIR" -name "*.jpg" | parallel --progress -j 4 "magick mogrify -resize \"${MAX_SIZE}x${MAX_SIZE}>\" -quality $QUALITY \"{}\""
    find "$TEMP_DIR" -name "*.jpg" | while read i; do
        echo "  $i"
        magick mogrify -resize "${MAX_SIZE}x${MAX_SIZE}>" -quality $QUALITY "$i"
    done
elif [[ "$QUALITY" != "90" ]]; then
    # Only set quality if it's different from the default and no resize is needed
    echo "Setting JPEG quality to $QUALITY without size change..."
    # find "$TEMP_DIR" -name "*.jpg" | parallel --progress -j 4 "magick mogrify -quality $QUALITY \"{}\""
    find "$TEMP_DIR" -name "*.jpg" | while read i; do
        echo "  $i"
        magick mogrify -quality $QUALITY "$i"
    done
fi
echo "Processing JPEG files done."

# Determine output filename
if [[ -z "$OUTPUT_FILE" ]]; then
    if $CONVERT_AVIF; then
        OUTPUT_FILE=$(echo "$fullname" | sed 's/AVIF/JPEG/')
    else
        OUTPUT_FILE="$fullname"
    fi
fi

# Ensure OUTPUT_FILE is an absolute path
if [[ "$OUTPUT_FILE" != /* ]]; then
    # Get the directory of the input file (which is now guaranteed to be absolute)
    input_dir=$(dirname "$fullname")
    # Use the same directory for the output file
    OUTPUT_FILE="$input_dir/$(basename "$OUTPUT_FILE")"
fi

# Backup original file if requested
if $BACKUP_ORIGINAL; then
    echo "Creating backup of original file..."
    mv "$fullname" "${fullname}.org"
fi

# Repack the archive
echo "Repacking archive to $OUTPUT_FILE..."
(cd "$TEMP_DIR" && zip -r "$OUTPUT_FILE" .)

# Clean up
rm -rf "$TEMP_DIR"

# Calculate new file size
filesize=$(wc -c "$OUTPUT_FILE" | awk '{print $1}')
(( new_filesize = filesize / 1024 / 1024 ))

# Display results
echo "Done!"
echo "File size: $org_filesize MB --> $new_filesize MB"
