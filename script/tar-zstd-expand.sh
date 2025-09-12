#!/bin/sh

#===============================================================================
#
#          FILE:  tar-zstd-expand.sh
#
#         USAGE:  ./tar-zstd-expand.sh TARGET_ARCHIVE
#                 ./tar-zstd-expand.sh --help
#
#   DESCRIPTION:  This script is deprecated. Use tar-zstd-compress.sh instead.
#                 tar-zstd-compress.sh automatically detects archive files and
#                 expands them when passed as TARGET_PATH.
#
#       OPTIONS:  --help    Show usage information.
#  REQUIREMENTS:  tar, zstd (gpg if expanding encrypted archives)
#          BUGS:  ---
#         NOTES:  DEPRECATED: Use tar-zstd-compress.sh for both compression and expansion.
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
  echo "DEPRECATED: This script is deprecated."
  echo "Use tar-zstd-compress.sh instead, which automatically detects and expands archives."
  echo ""
  echo "New usage:"
  echo "  ./tar-zstd-compress.sh myfile.tar.zst"
  echo "  ./tar-zstd-compress.sh myfile.tar.zst.gpg"
  echo ""
  echo "Legacy usage (still works but deprecated):"
  echo "  $0 TARGET_ARCHIVE"
  echo "  $0 --help"
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

# Show deprecation warning and redirect to new script
echo "DEPRECATED: tar-zstd-expand.sh is deprecated."
echo "Redirecting to tar-zstd-compress.sh which now handles both compression and expansion..."
echo ""

# Get the directory of this script to find tar-zstd-compress.sh
SCRIPT_DIR="$(dirname "$0")"

# Check if target archive is provided
if [ -z "$TARGET_ARCHIVE" ]; then
  echo "Error: Target archive not specified." >&2
  usage
fi

# Redirect to tar-zstd-compress.sh
exec "$SCRIPT_DIR/tar-zstd-compress.sh" "$TARGET_ARCHIVE"

exit 0