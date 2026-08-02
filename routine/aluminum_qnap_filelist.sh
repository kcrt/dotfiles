#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  aluminum_qnap_filelist.sh
#         USAGE:  ./aluminum_qnap_filelist.sh
#   DESCRIPTION:  Refresh the local copy of the QNAP file list, dropping the
#                 macOS/QNAP metadata entries that are not worth keeping.
#  REQUIREMENTS:  pv, /Volumes/Backup mounted
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

# Check if machine is aluminum
if [[ "$HOST" != "aluminum.local" ]]; then
    OSNotify "This script is intended to be run on aluminum.local only."
    exit 1
fi

if ! command -v pv > /dev/null 2>&1; then
    OSError "pv is not installed. Please install it first."
    exit 1
fi

QNAP_FILELIST=/Volumes/Backup/QnapFileList.txt
if [[ ! -f "$QNAP_FILELIST" ]]; then
    OSError "$QNAP_FILELIST not found. Is /Volumes/Backup mounted?"
    exit 1
fi

OSNotify "/Volumes/Backup/ mounted, refreshing QnapFileList.txt..."
# Without pipe_fail the status would be sort's, so a failing pv goes unnoticed.
setopt local_options pipe_fail
# Build the list in a temporary file: the redirection truncates its target
# before the pipeline even starts, which would destroy the previous list.
QNAP_FILELIST_TMP="${TMPDIR:-/tmp}/QnapFileList.txt.$$"
if pv "$QNAP_FILELIST" | grep -Ev 'AppleDouble|\._|DS_Store|\.@__thumb' | LANG=C sort > "$QNAP_FILELIST_TMP"; then
    mv "$QNAP_FILELIST_TMP" ~/QnapFileList.txt
    echo_ok "QnapFileList.txt refreshed ($(wc -l < ~/QnapFileList.txt | tr -d ' ') entries)."
else
    rm -f "$QNAP_FILELIST_TMP"
    OSError "Failed to refresh QnapFileList.txt. The existing file is kept."
    exit 1
fi
