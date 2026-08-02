#!/usr/bin/env zsh

source ${DOTFILES}/script/OSNotify.sh

OSNotify "Anti-virus database updating..."
freshclam || count_failure "freshclam failed to update the virus database."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # clamscan --infected --cross-fs=no --recursive ~/Downloads # ~/Documents ~/Desktop
    echo_warn "Scanning is disabled on macOS; only the database was updated."
else
    OSNotify "Scanning system. This may take a while..."
    # clamscan exits 1 when it finds an infected file. The old code tested $?
    # after the if/else, which is the status of the if statement itself, so a
    # find would never have been noticed.
    if ! clamscan --infected --cross-fs=no --recursive "$HOME"; then
        count_failure "!!! Virus found !!!"
        # Only stop for a human when there is one; a background run would hang.
        if [[ -t 0 ]]; then
            echo "Please check message. Press Enter key to continue..."
            read
        fi
    fi
fi

routine_exit_status
