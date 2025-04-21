#!/bin/bash

# macOS Sparse Bundle Creator Script
# Interactive script to create sparse bundle disk images

echo "===== macOS Sparse Bundle Creator ====="
echo ""

# Default values
DEFAULT_SIZE="10g"
DEFAULT_FS="APFS"
DEFAULT_VOLNAME="MyVolume"
DEFAULT_BAND_SIZE="8388608"  # 8MB (bytes)
DEFAULT_FILENAME="MyDiskImage.sparsebundle"
DEFAULT_LOCATION="${HOME}/Desktop"

# Input disk image size
read -p "Enter disk image size (e.g., 10g, 500m, 1t) [Default: ${DEFAULT_SIZE}]: " SIZE
SIZE=${SIZE:-$DEFAULT_SIZE}

# Select file system
echo "Select file system:"
echo "1) APFS (recommended)"
echo "2) HFS+ (Mac OS Extended)"
echo "3) FAT32 (MS-DOS)"
echo "4) ExFAT"
read -p "Selection (1-4) [Default: 1]: " FS_CHOICE
case $FS_CHOICE in
    2) FS="HFS+" ;;
    3) FS="FAT32" ;;
    4) FS="ExFAT" ;;
    *) FS="$DEFAULT_FS" ;;
esac

# Input volume name
read -p "Enter volume name [Default: ${DEFAULT_VOLNAME}]: " VOLNAME
VOLNAME=${VOLNAME:-$DEFAULT_VOLNAME}

# Select band size
echo "Select band size (larger sizes are better for large files):"
echo "1) 8MB (default)"
echo "2) 16MB"
echo "3) 32MB"
echo "4) 64MB"
echo "5) 128MB"
echo "6) Custom (specify in bytes)"
read -p "Selection (1-6) [Default: 1]: " BAND_CHOICE
case $BAND_CHOICE in
    2) BAND_SIZE="32768" ;;    # 16MB
    3) BAND_SIZE="65536" ;;    # 32MB
    4) BAND_SIZE="131072" ;;    # 64MB
    5) BAND_SIZE="262144" ;;   # 128MB
    6) read -p "Enter band size in 512-bytes (e.g., 65536 = 32MB): " CUSTOM_BAND_SIZE
       BAND_SIZE=${CUSTOM_BAND_SIZE:-$DEFAULT_BAND_SIZE} ;;
    *) BAND_SIZE="$DEFAULT_BAND_SIZE" ;;
esac

# Select encryption
echo "Use encryption?"
echo "1) None"
echo "2) AES-128"
echo "3) AES-256 (strongest)"
read -p "Selection (1-3) [Default: 1]: " ENCRYPTION_CHOICE
case $ENCRYPTION_CHOICE in
    2) ENCRYPTION="-encryption AES-128" ;;
    3) ENCRYPTION="-encryption AES-256" ;;
    *) ENCRYPTION="" ;;
esac

# Input filename
read -p "Enter disk image filename [Default: ${DEFAULT_FILENAME}]: " FILENAME
FILENAME=${FILENAME:-$DEFAULT_FILENAME}

# Select save location
read -p "Save location [Default: ${DEFAULT_LOCATION}]: " LOCATION
LOCATION=${LOCATION:-$DEFAULT_LOCATION}

# Create final path
FULL_PATH="${LOCATION}/${FILENAME}"

# Build command
if [ -n "$ENCRYPTION" ]; then
    CMD="hdiutil create -size $SIZE -fs $FS -volname \"$VOLNAME\" -type SPARSEBUNDLE $ENCRYPTION -imagekey sparse-band-size=$BAND_SIZE \"$FULL_PATH\""
else
    CMD="hdiutil create -size $SIZE -fs $FS -volname \"$VOLNAME\" -type SPARSEBUNDLE -imagekey sparse-band-size=$BAND_SIZE \"$FULL_PATH\""
fi

# Confirm settings
echo ""
echo "===== Confirmation ====="
echo "Size: $SIZE"
echo "File system: $FS"
echo "Volume name: $VOLNAME"
echo "Band size: $BAND_SIZE bytes ($(( BAND_SIZE / 1024 / 1024 ))MB)"
if [ -n "$ENCRYPTION" ]; then
    echo "Encryption: ${ENCRYPTION#-encryption }"
else
    echo "Encryption: None"
fi
echo "File path: $FULL_PATH"
echo ""
echo "Command to execute:"
echo "$CMD"
echo ""

# Confirm execution
read -p "Create sparse bundle with these settings? (y/n) [Default: y]: " CONFIRM
CONFIRM=${CONFIRM:-"y"}

if [[ $CONFIRM =~ ^[Yy] ]]; then
    echo "Creating disk image..."
    eval $CMD
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "Disk image successfully created: $FULL_PATH"
        
        # Mount option
        read -p "Mount the newly created disk image now? (y/n) [Default: y]: " MOUNT
        MOUNT=${MOUNT:-"y"}
        
        if [[ $MOUNT =~ ^[Yy] ]]; then
            hdiutil attach "$FULL_PATH"
            echo "Disk image has been mounted."
        fi
    else
        echo ""
        echo "Error: Failed to create disk image."
    fi
else
    echo "Operation cancelled."
fi
