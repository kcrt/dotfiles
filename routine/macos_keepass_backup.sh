#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  macos_keepass_backup.sh
#         USAGE:  ./macos_keepass_backup.sh
#   DESCRIPTION:  Copy the KeePass database to every backup destination. This is
#                 the most important thing we copy around, so each destination
#                 is verified and any failure is reported loudly.
#  REQUIREMENTS:  gcloud (for the Google Cloud Storage copy)
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

KEEPASS_DB=~/Documents/passwords.kdbx
KEEPASS_GENERATIONS=20

# A password backup that quietly did not happen is the worst outcome here, so
# every destination is attempted and every failure is counted.
backup_keepass(){
    local dest="$1"
    if [[ ! -d "${dest:h}" ]]; then
        count_failure "KeePass backup directory not found: ${dest:h}"
        return 1
    fi
    if cp "$KEEPASS_DB" "$dest"; then
        echo_ok "passwords.kdbx -> $dest"
    else
        count_failure "Failed to copy passwords.kdbx to $dest"
        return 1
    fi
}

if [[ ! -f "$KEEPASS_DB" ]]; then
    OSError "$KEEPASS_DB not found. Skipping password backup."
    exit 1
fi

backup_keepass "$HOME/Library/Mobile Documents/iCloud~be~kyuran~kypass2/Documents/passwords.kdbx"

if gcloud storage cp "$KEEPASS_DB" gs://auto.backup.kcrt.net/auto/passwords.kdbx; then
    echo_ok "passwords.kdbx -> gs://auto.backup.kcrt.net/auto/"
else
    count_failure "Failed to upload passwords.kdbx to Google Cloud Storage."
fi

if [[ -d /Volumes/Backup/passwords ]]; then
    if backup_keepass "/Volumes/Backup/passwords/passwords-$(date +%Y%m%d).kdbx"; then
        # (NOn): skip if empty, sort by name descending == newest first
        kdbx_generations=(/Volumes/Backup/passwords/passwords-*.kdbx(NOn))
        if (( ${#kdbx_generations} > KEEPASS_GENERATIONS )); then
            echo_info "Removing $(( ${#kdbx_generations} - KEEPASS_GENERATIONS )) old generation(s) of passwords.kdbx..."
            rm -v -f -- "${kdbx_generations[@]:$KEEPASS_GENERATIONS}"
        fi
    fi
else
    count_failure "/Volumes/Backup/passwords not found. Skipping dated backup."
fi

routine_exit_status
