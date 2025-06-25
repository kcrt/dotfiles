#!/bin/sh

#===============================================================================
#
#          FILE:  tar-zstd-expand.sh
#
#         USAGE:  ./tar-zstd-expand.sh TARGET_ARCHIVE
#                 ./tar-zstd-expand.sh --help
#
#   DESCRIPTION:  Expands archives compressed with tar-zstd-compress.sh.
#                 Supports both .tar.zst and .tar.zst.gpg files.
#
#       OPTIONS:  --help    Show usage information.
#  REQUIREMENTS:  tar, zstd (gpg if expanding encrypted archives)
#          BUGS:  ---
#         NOTES:  ---
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

# Function to display help message
usage() {
  echo "Usage: $0 TARGET_ARCHIVE"
  echo "       $0 --help"
  echo ""
  echo "Expands archives created with tar-zstd-compress.sh."
  echo "Supports both .tar.zst and .tar.zst.gpg files."
  echo ""
  echo "Options:"
  echo "  --help                Show this help message."
  echo ""
  echo "Supported archive types:"
  echo "  .tar.zst              Standard zstd compressed tar archive"
  echo "  .tar.zst.gpg          GPG encrypted zstd compressed tar archive"
  echo ""
  echo "Examples:"
  echo "  $0 myfile.tar.zst"
  echo "  $0 myfile.tar.zst.gpg"
  exit 1
}

# Parse arguments
TARGET_ARCHIVE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --help)
      usage
      ;;
    -*)
      echo "Error: Unknown option: $1" >&2
      usage
      ;;
    *)
      if [ -z "$TARGET_ARCHIVE" ]; then
        TARGET_ARCHIVE="$1"
      else
        echo "Error: Multiple archives specified." >&2
        usage
      fi
      shift
      ;;
  esac
done

# Check if target archive is provided
if [ -z "$TARGET_ARCHIVE" ]; then
  echo "Error: Target archive not specified." >&2
  usage
fi

# Check if target archive exists
if [ ! -f "$TARGET_ARCHIVE" ]; then
    echo "Error: Archive '$TARGET_ARCHIVE' not found." >&2
    exit 1
fi

# Determine archive type and expand accordingly
if [[ "$TARGET_ARCHIVE" == *.tar.zst.gpg ]]; then
  echo "Detected encrypted archive: '$TARGET_ARCHIVE'. Expanding..."
  # Check if gpg is available
  if ! command -v gpg >/dev/null 2>&1; then
    echo "Error: gpg command not found, required to decrypt '$TARGET_ARCHIVE'." >&2
    exit 1
  fi
  gpg -d "$TARGET_ARCHIVE" | tar -xvf -
  echo "Expansion complete."
elif [[ "$TARGET_ARCHIVE" == *.tar.zst ]]; then
  echo "Detected archive: '$TARGET_ARCHIVE'. Expanding..."
  tar -xvf "$TARGET_ARCHIVE"
  echo "Expansion complete."
else
  echo "Error: Unsupported archive format. Only .tar.zst and .tar.zst.gpg files are supported." >&2
  exit 1
fi

exit 0