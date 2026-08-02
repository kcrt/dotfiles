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

# Homebrew's rsync, not the ancient one in /usr/bin.
run_rsync() {
    local rc=0
    /opt/homebrew/bin/rsync "$@" || rc=$?
    # 24 = "partial transfer due to vanished source files". Caches and temp
    # files disappearing mid-run is normal here, so it is not a failure.
    if (( rc != 0 && rc != 24 )); then
        count_failure "rsync failed (exit $rc): ${@[-1]}"
        return $rc
    fi
    return 0
}

backup_directory_mount() {
    local src_dir=$1
    local dest_dir=$2
    # iconv is required to convert file names from UTF-8 to UTF-8-MAC.
    # (seems strage, but UTF-8-MAC,UTF-8 does not work)
    # This is required to avoid resending files again and again.
    run_rsync -ahv \
        --exclude="site-packages/" --exclude=".git/" --exclude=".DS_Store" --exclude="packrat/" --exclude=".tmp.driveupload" --exclude="venv/" --exclude=".venv/" --exclude=".pio/" --exclude="node_modules/" --exclude="dist/" --exclude=".next/" --exclude=".expo" --exclude="Arduino/libraries/" --exclude=".mypy_cache" \
        --info=progress2 --no-inc-recursive --delete --no-o --no-p --no-g \
        --iconv=UTF-8,UTF-8-MAC \
        "$src_dir" "/Volumes/Backup/$dest_dir"
}
# Volume roots carry these root-owned directories. rsync cannot read them, which
# costs an exit 23 and, worse, makes rsync skip --delete for the whole transfer.
VOLUME_METADATA_EXCLUDES=(
    --exclude=".Spotlight-V100" --exclude=".Trashes" --exclude=".fseventsd"
    --exclude=".DocumentRevisions-V100" --exclude=".TemporaryItems"
)

# backup_directory_rsync <src> <dest> [extra rsync options...]
backup_directory_rsync() {
    local src_dir=$1
    local dest_dir=$2
    shift 2
    if [[ "$src_dir" != */ ]]; then
        src_dir="$src_dir/"
    fi
    # -z sometimes causes problems with large files, so we disable it.
    run_rsync -ahv \
        --exclude="site-packages/" --exclude=".git/" --exclude=".DS_Store" --exclude="packrat/" --exclude=".tmp.driveupload" --exclude="venv/" --exclude=".venv/" \
        --exclude=".pio/" --exclude="node_modules/" --exclude="dist/" --exclude=".next/" --exclude=".expo" --exclude="Arduino/libraries/" --exclude=".mypy_cache" --exclude="*/.@__thumb/" --exclude=".rustup" \
		--exclude="Library/pnpm" \
        "${VOLUME_METADATA_EXCLUDES[@]}" "$@" \
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
    OSNotify "Mail -> Qnap"
    backup_directory_rsync ~/Library/Mail/ Mail
    # /nosync and its Parallels subdirectory are one pair: Parallels is excluded
    # here and sent by the dedicated transfer right below. Keep the two together,
    # because dropping the --exclude would silently back up 177G of disk images
    # twice, without --inplace.
    OSNotify "nosync -> Qnap"
    backup_directory_rsync /nosync/ nosync --exclude="Parallels/"

    # A single Parallels disk image is ~177G and changes whenever the VM runs.
    # --inplace rewrites only the changed blocks; without it the NAS would have
    # to write out the whole image every time. The trade-off is that an
    # interrupted transfer leaves the destination image in a mixed state, which
    # --partial lets the next run repair.
    OSNotify "Parallels -> Qnap"
    run_rsync -ahv \
        --info=progress2 --no-inc-recursive --delete --no-o --no-p --no-g \
        --inplace --partial --block-size=128K \
        /nosync/Parallels/ "kcrt@qnap.local:/share/Backup/Parallels"
fi

# Let maintain.sh's run_step know that something did not make it to the NAS.
routine_exit_status
