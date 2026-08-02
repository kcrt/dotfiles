#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  generic_clamscan_update_and_scan.sh
#         USAGE:  ./generic_clamscan_update_and_scan.sh
#   DESCRIPTION:  Update the ClamAV signatures and scan for malware.
#  REQUIREMENTS:  clamav (freshclam, clamd, clamdscan)
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

# What to scan. ~/Downloads is where anything from outside lands.
SCAN_TARGETS=(~/Downloads)

OSNotify "Anti-virus database updating..."
freshclam || count_failure "freshclam failed to update the virus database."

# clamscan is single threaded and reloads the 3.3M signature database on every
# run: ~/Downloads (5G, ~12k files) takes over ten minutes on one core. clamd
# with clamdscan --multiscan spreads the same work over the whole machine, so
# run the daemon just for this scan. Its config in /opt/homebrew/etc is empty
# and belongs to Homebrew, so use a throwaway one of our own.
clamd_dir="${TMPDIR:-/tmp}/maintain_clamd.$$"
clamd_conf="$clamd_dir/clamd.conf"
clamd_pidfile="$clamd_dir/clamd.pid"
clamd_socket="$clamd_dir/clamd.sock"

# Whatever happens - success, failure, Ctrl-C - the daemon must not outlive us.
stop_clamd() {
    if [[ -f "$clamd_pidfile" ]]; then
        local pid=$(<"$clamd_pidfile")
        kill "$pid" 2>/dev/null
        local waited=0
        while kill -0 "$pid" 2>/dev/null && (( waited < 20 )); do
            sleep 0.5
            (( waited++ ))
        done
        kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
    fi
    rm -rf "$clamd_dir"
}
trap stop_clamd EXIT INT TERM

start_clamd() {
    mkdir -p "$clamd_dir" || return 1
    cat > "$clamd_conf" <<EOF
LocalSocket $clamd_socket
PidFile $clamd_pidfile
LogFile $clamd_dir/clamd.log
MaxThreads 8
EOF
    clamd --config-file="$clamd_conf" || return 1
    # clamd forks immediately but needs a few seconds to load the database.
    local waited=0
    while [[ ! -S "$clamd_socket" ]] && (( waited < 120 )); do
        sleep 0.5
        (( waited++ ))
    done
    [[ -S "$clamd_socket" ]]
}

OSNotify "Scanning ${SCAN_TARGETS[*]}. This may take a while..."
if start_clamd; then
    # clamdscan exits 1 when it finds an infected file, 2 on error.
    clamdscan --multiscan --fdpass --config-file="$clamd_conf" "${SCAN_TARGETS[@]}"
    scan_status=$?
    case $scan_status in
        0) echo_ok "No malware found." ;;
        1) count_failure "!!! Virus found !!!"
           # Only stop for a human when there is one; a background run would hang.
           if [[ -t 0 ]]; then
               echo "Please check message. Press Enter key to continue..."
               read
           fi ;;
        *) count_failure "clamdscan failed (exit $scan_status). See $clamd_dir/clamd.log" ;;
    esac
else
    count_failure "Could not start clamd; skipping the scan."
fi

routine_exit_status
