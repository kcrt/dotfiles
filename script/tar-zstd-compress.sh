#!/bin/sh

#===============================================================================
#
#          FILE:  tar-zstd-compress-encrypt.sh
#
#         USAGE:  ./tar-zstd-compress-encrypt.sh [--encrypt] TARGET_PATH
#                 ./tar-zstd-compress-encrypt.sh --help
#
#   DESCRIPTION:  Compresses the TARGET_PATH (file or directory) into TARGET_PATH.tar.zst using tar and zstd.
#                 If --encrypt is specified, it also encrypts the archive using GPG,
#                 resulting in TARGET_PATH.tar.zst.gpg.
#
#       OPTIONS:  --encrypt Encrypt the output using GPG (requires gpg).
#                 --help    Show usage and expansion instructions.
#  REQUIREMENTS:  tar, zstd (gpg if --encrypt is used)
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
  echo "To expand the archive:"
  echo "  Without encryption: tar -xvf TARGET_PATH.tar.zst"
  echo "  With encryption:    gpg -d TARGET_PATH.tar.zst.gpg | tar -xvf -"
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
  tar -xvf "$TARGET_PATH"
  echo "Expansion complete."
  exit 0
fi

# Perform compression (and optionally encryption)
if [ "$ENCRYPT" = true ]; then
  echo "Compressing and encrypting '$TARGET_PATH' to '$TARGET_FILENAME' for recipient '$RECIPIENT'..."
  # Check if gpg is available
  if ! command -v gpg >/dev/null 2>&1; then
    echo "Error: gpg command not found, but --encrypt option was specified." >&2
    exit 1
  fi
  if [ "$USE_LONG" = true ]; then
    tar --verbose -c -f - "$TARGET_PATH" | zstd -T0 -$COMPRESSION_LEVEL --long=31 | gpg --encrypt --recipient "$RECIPIENT" --output "$TARGET_FILENAME"
  else
    tar --verbose -c -f - "$TARGET_PATH" | zstd -T0 -$COMPRESSION_LEVEL | gpg --encrypt --recipient "$RECIPIENT" --output "$TARGET_FILENAME"
  fi
  echo "Compression and encryption complete: '$TARGET_FILENAME'"
else
  echo "Compressing '$TARGET_PATH' to '$TARGET_FILENAME'..."
  if [ "$USE_LONG" = true ]; then
    tar --verbose -c -f - "$TARGET_PATH" | zstd -T0 -$COMPRESSION_LEVEL --long=31 > "$TARGET_FILENAME"
  else
    tar --verbose -c -f - "$TARGET_PATH" | zstd -T0 -$COMPRESSION_LEVEL > "$TARGET_FILENAME"
  fi
  echo "Compression complete: '$TARGET_FILENAME'"
fi

exit 0
