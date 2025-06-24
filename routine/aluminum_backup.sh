#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  aluminum_backup.sh
#         USAGE:  ./aluminum_backup.sh
#   DESCRIPTION:  This script is a backup utility for aluminum files.
#  REQUIREMENTS:  rsync
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

# Check if rsync is installed
if ! command -v rsync &> /dev/null; then
    OSNotify "rsync is not installed. Please install it first."
    exit 1
fi

# Check if machine is aluminum
if [[ "$HOST" != "aluminum.local" ]]; then
    OSNotify "This script is intended to be run on aluminum.local only."
    exit 1
fi

# Check if qnap is reachable
if ! ping -c 1 qnap.local &> /dev/null; then
    OSNotify "QNAP is not reachable. Please check your network connection."
    exit 1
fi

backup_directory_mount() {
    local src_dir=$1
    local dest_dir=$2
    # iconv is required to convert file names from UTF-8 to UTF-8-MAC.
    # (seems strage, but UTF-8-MAC,UTF-8 does not work)
    # This is required to avoid resending files again and again.
    /opt/homebrew/bin/rsync -ahv \
        --exclude="site-packages/" --exclude=".git/" --exclude=".DS_Store" --exclude="packrat/" --exclude=".tmp.driveupload" --exclude="venv/" --exclude=".venv/" --exclude=".pio/" --exclude="node_modules/" --exclude="dist/" --exclude=".next/" --exclude=".expo" --exclude="Arduino/libraries/" --exclude=".mypy_cache" \
        --info=progress2 --no-inc-recursive --delete --no-o --no-p --no-g \
        --iconv=UTF-8,UTF-8-MAC \
        "$src_dir" "/Volumes/Backup/$dest_dir"
}
backup_directory_rsync() {
    local src_dir=$1
    local dest_dir=$2
    if [[ "$src_dir" != */ ]]; then
        src_dir="$src_dir/"
    fi
    # -z sometimes causes problems with large files, so we disable it.
    /opt/homebrew/bin/rsync -ahv \
        --exclude="site-packages/" --exclude=".git/" --exclude=".DS_Store" --exclude="packrat/" --exclude=".tmp.driveupload" --exclude="venv/" --exclude=".venv/" \
        --exclude=".pio/" --exclude="node_modules/" --exclude="dist/" --exclude=".next/" --exclude=".expo" --exclude="Arduino/libraries/" --exclude=".mypy_cache" --exclude="*/.@__thumb/" --exclude=".rustup" \
		--exclude="Library/pnpm" \
        --info=progress2 --no-inc-recursive --delete --no-o --no-p --no-g \
        "$src_dir" "kcrt@qnap.local:/share/Backup/$dest_dir"
}

if [[ -d /Volumes/Backup/ ]]; then
    OSNotify "prog -> Qnap"
    backup_directory_rsync ~/prog/ prog
    OSNotify "Documents -> Qnap"
    backup_directory_rsync ~/Documents/ Documents
    OSNotify "diskimage -> Qnap"
    backup_directory_rsync ~/diskimages/ diskimages
    OSNotify "Calibre -> Qnap"
    backup_directory_rsync ~/Calibre/ Calibre
    OSNotify "Pictures -> Qnap"
    backup_directory_rsync ~/Pictures/ Pictures
    OSNotify "Zotero -> Qnap"
    backup_directory_rsync ~/Zotero/ Zotero
    
    # Because Parallels disk images are extremely large, we use a different method.
    OSNotify "Parallels -> Qnap"
    /opt/homebrew/bin/rsync -ahv \
        --info=progress2 --no-inc-recursive --delete --no-o --no-p --no-g \
        --inplace --partial --block-size=128K \
        ~/Parallels/ "kcrt@qnap.local:/share/Backup/Parallels"
fi
