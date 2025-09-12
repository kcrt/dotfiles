#!/bin/bash

#===============================================================================
#
#          FILE:  tar-zstd-compress.sh
#
#         USAGE:  ./tar-zstd-compress.sh [--encrypt [--recipient EMAIL]] [--fast | --eager] [--long] TARGET_PATH
#                 ./tar-zstd-compress.sh --help
#
#   DESCRIPTION:  Compresses the TARGET_PATH (file or directory) into TARGET_PATH.tar.zst using tar and zstd.
#                 If --encrypt is specified, it also encrypts the archive using GPG,
#                 resulting in TARGET_PATH.tar.zst.gpg.
#                 If supecified file is archive, it will be expanded instead.
#
#       OPTIONS:  --encrypt         Encrypt the output using GPG (requires gpg).
#                 --recipient EMAIL Specify the GPG recipient email.
#                 --fast            Use faster compression (level 1).
#                 --eager           Use higher compression (level 19).
#                 --long            Use long distance matching with window size 31.
#                 --help            Show usage and expansion instructions.
#  REQUIREMENTS:  tar, zstd (gpg if --encrypt is used, pv if available)
#          BUGS:  ---
#         NOTES:  Recipient for encryption is hardcoded to kcrt@kcrt.net
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

set -e # Exit immediately if a command exits with a non-zero status.

# Check if required commands are available
if ! command -v tar >/dev/null 2>&1; then
  echo "Error: tar command not found. Please install tar first." >&2
  exit 1
fi

if ! command -v zstd >/dev/null 2>&1; then
  echo "Error: zstd command not found. Please install zstd first." >&2
  exit 1
fi

if command -v pv >/dev/null 2>&1; then
  USE_PV=true
else
  USE_PV=false
fi

# Function to get file/directory size in bytes
get_size() {
  target="$1"
  if [ -d "$target" ]; then
    # For directories, sum all file sizes
    if command -v gdu >/dev/null 2>&1; then
      # Use GNU du if available (Linux/BSD)
      gdu -sb "$target" | cut -f1
    elif du -sb "$target" >/dev/null 2>&1; then
      # Try GNU du syntax first
      du -sb "$target" | cut -f1
    else
      # macOS fallback: use find with stat
      find "$target" -type f -exec stat -f%z {} \; | awk '{sum += $1} END {print sum+0}'
    fi
  else
    # For files, use stat with OS-specific format
    if stat -c%s "$target" >/dev/null 2>&1; then
      # Linux format
      stat -c%s "$target"
    else
      # macOS format
      stat -f%z "$target"
    fi
  fi
}

# Function to format bytes into human-readable size
format_size() {
  bytes="$1"
  if [ "$bytes" -ge 1073741824 ]; then
    echo "$(( bytes / 1073741824 ))GB"
  elif [ "$bytes" -ge 1048576 ]; then
    echo "$(( bytes / 1048576 ))MB"
  elif [ "$bytes" -ge 1024 ]; then
    echo "$(( bytes / 1024 ))KB"
  else
    echo "${bytes}B"
  fi
}

# Default values
ENCRYPT=false
TARGET_PATH=""
RECIPIENT="kcrt@kcrt.net" # Default recipient
COMPRESSION_LEVEL=3 # Default zstd compression level
USE_LONG=false # Flag for --long option

# Function to display help message
usage() {
  echo "Usage: $0 [--encrypt [--recipient RECIPIENT_EMAIL]] [--fast | --eager] [--long] TARGET_PATH"
  echo "       $0 --help"
  echo ""
  echo "Compresses TARGET_PATH (file or directory) using tar with zstd compression."
  echo "If --encrypt is specified, the archive is also encrypted using GPG."
  echo ""
  echo "Options:"
  echo "  --encrypt             Encrypt the output using GPG (requires gpg)."
  echo "  --recipient EMAIL     Specify the GPG recipient email (default: $RECIPIENT)."
  echo "  --fast                Use faster compression (level 1)."
  echo "  --eager               Use higher compression (level 19)."
  echo "  --long                Use long distance matching with window size 31."
  echo "  --help                Show this help message."
  echo ""
  echo "Output file:"
  echo "  TARGET_PATH.tar.zst (without encryption)"
  echo "  TARGET_PATH.tar.zst.gpg (with encryption)"
  echo ""
  echo "To expand the archive, simplely use this script or:"
  echo "  Without encryption: tar -xvf TARGET_PATH.tar.zst"
  echo "  With encryption:    gpg -d TARGET_PATH.tar.zst.gpg | tar -xvf -"
  echo "  (use --use-compress-program=\"zstd -d --memory=2048MB\" for archive created with --long)"
  exit 1
}

# Parse arguments
while [ "$#" -gt 0 ]; do
  case "$1" in
    --encrypt)
      ENCRYPT=true
      shift
      ;;
    --recipient)
      if [ -z "$2" ] || [[ "$2" == -* ]]; then # Check if argument is missing or is another option
        echo "Error: --recipient requires an email address argument." >&2
        usage
      fi
      RECIPIENT="$2"
      shift 2
      ;;
    --fast)
      COMPRESSION_LEVEL=1
      shift
      ;;
    --eager)
      COMPRESSION_LEVEL=19
      shift
      ;;
    --long)
      USE_LONG=true
      shift
      ;;
    --help)
      usage
      ;;
    -*)
      echo "Error: Unknown option: $1" >&2
      usage
      ;;
    *)
      if [ -z "$TARGET_PATH" ]; then
        TARGET_PATH="$1"
      else
        echo "Error: Multiple target paths specified." >&2
        usage
      fi
      shift
      ;;
  esac
done

# Check if target path is provided
if [ -z "$TARGET_PATH" ]; then
  echo "Error: Target path not specified." >&2
  usage
fi

# Check if the target is an archive to be expanded
if [[ "$TARGET_PATH" == *.tar.zst.gpg ]]; then
  echo "Detected encrypted archive: '$TARGET_PATH'. Expanding..."
  # Check if gpg is available
  if ! command -v gpg >/dev/null 2>&1; then
    echo "Error: gpg command not found, required to decrypt '$TARGET_PATH'." >&2
    exit 1
  fi
  gpg -d "$TARGET_PATH" | tar -xvf -
  echo "Expansion complete."
  exit 0
elif [[ "$TARGET_PATH" == *.tar.zst ]]; then
  echo "Detected archive: '$TARGET_PATH'. Expanding..."
  tar -xvf "$TARGET_PATH" --use-compress-program="zstd -d --memory=2048MB"
  echo "Expansion complete."
  exit 0
fi


# Remove trailing slash if the target is a directory and has a trailing slash
# This ensures consistent output filenames like 'mydir.tar.zst' instead of 'mydir/.tar.zst'
TARGET_BASE="${TARGET_PATH%/}"

# Determine target filename based on encryption flag
if [ "$ENCRYPT" = true ]; then
  TARGET_FILENAME="${TARGET_BASE}.tar.zst.gpg"
else
  TARGET_FILENAME="${TARGET_BASE}.tar.zst"
fi

# Check if target path exists (file or directory)
if [ ! -e "$TARGET_PATH" ]; then
    echo "Error: Target path '$TARGET_PATH' not found." >&2
    exit 1
fi

# Get size for progress display
echo "Calculating size..."
BEFORE_SIZE=$(get_size "$TARGET_PATH")

# Build zstd flags
zstd_flags="-T0 -$COMPRESSION_LEVEL"
if [ "$USE_LONG" = true ]; then
  zstd_flags="$zstd_flags --long=31"
fi

# Perform compression (and optionally encryption)
if [ "$ENCRYPT" = true ]; then
  echo "Compressing and encrypting '$TARGET_PATH' to '$TARGET_FILENAME' for recipient '$RECIPIENT'..."
  # Check if gpg is available
  if ! command -v gpg >/dev/null 2>&1; then
    echo "Error: gpg command not found, but --encrypt option was specified." >&2
    exit 1
  fi
  if [ "$USE_PV" = true ]; then
    tar -c -f - "$TARGET_PATH" | pv -s "$BEFORE_SIZE" | zstd $zstd_flags | gpg --encrypt --recipient "$RECIPIENT" --output "$TARGET_FILENAME"
  else
    tar -c -f - "$TARGET_PATH" | zstd $zstd_flags | gpg --encrypt --recipient "$RECIPIENT" --output "$TARGET_FILENAME"
  fi
  echo "Compression and encryption complete: '$TARGET_FILENAME'"
else
  echo "Compressing '$TARGET_PATH' to '$TARGET_FILENAME'..."
  if [ "$USE_PV" = true ]; then
    tar -c -f - "$TARGET_PATH" | pv -s "$BEFORE_SIZE" | zstd $zstd_flags > "$TARGET_FILENAME"
  else
    tar -c -f - "$TARGET_PATH" | zstd $zstd_flags > "$TARGET_FILENAME"
  fi
  echo "Compression complete: '$TARGET_FILENAME'"
fi

# Display size change
AFTER_SIZE=$(get_size "$TARGET_FILENAME")
REDUCTION=$(( BEFORE_SIZE - AFTER_SIZE ))
PERCENTAGE=$(( (REDUCTION * 100) / BEFORE_SIZE ))
BEFORE_FORMATTED=$(format_size "$BEFORE_SIZE")
AFTER_FORMATTED=$(format_size "$AFTER_SIZE")
echo "Size reduced from $BEFORE_FORMATTED to $AFTER_FORMATTED (${PERCENTAGE}% compression)"

exit 0
