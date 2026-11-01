#!/bin/sh

# Temporarily allow passwordless sudo (e.g. for non-interactive sudo over ssh), with automatic expiry.
# MODIFIES the system: writes /etc/sudoers.d/zz-allow-sudo-temp and /etc/tmpfiles.d/allow-sudo.conf.
# Target: Linux hosts with systemd (Ubuntu). Runs as root via sudo on the host itself, or from another
# machine with "allow-sudo.sh HOST grant", which sends this script over ssh (the host need not have it).

SUDOERS_FILE=/etc/sudoers.d/zz-allow-sudo-temp
TMPFILES_FILE=/etc/tmpfiles.d/allow-sudo.conf
REVOKE_UNIT=allow-sudo-revoke
DEFAULT_DURATION=30m

usage() {
    cat <<EOF
Usage: $(basename "$0") HOST grant [DURATION] | revoke | status    (from another machine, via ssh)
       sudo ~/dotfiles/script/$(basename "$0") grant [DURATION] | revoke | status    (on the host)

Temporarily grants NOPASSWD sudo to the invoking user (\$SUDO_USER).
Use the full path with sudo: sudo's secure_path does not include ~/dotfiles/script.

  grant [DURATION]  Allow passwordless sudo for DURATION (systemd time span:
                    30m, 1h, 90min ...; default: $DEFAULT_DURATION). Granting again
                    resets the expiry.
  revoke            Remove the permission immediately.
  status            Show whether the permission is active and when it expires.

Expiry is enforced twice:
  - a transient systemd timer ($REVOKE_UNIT) deletes $SUDOERS_FILE, and
  - $TMPFILES_FILE deletes it at boot (transient timers do not survive reboot).

With HOST, runs "ssh -t HOST sudo ..." with this local copy of the script (you type the sudo
password on HOST once for grant). Example: $(basename "$0") boron.local grant 1h
EOF
}

run_on_host() {
    host=$1
    shift
    case "${1:-}" in
        grant|revoke|status) ;;
        *) usage >&2; exit 1 ;;
    esac
    # Arguments are interpolated into the remote shell command, so allow only plain tokens.
    for arg in "$@"; do
        if ! echo "$arg" | grep -Eq '^[A-Za-z0-9]+$'; then
            echo "error: invalid argument: $arg" >&2
            exit 1
        fi
    done
    payload=$(base64 < "$0" | tr -d '\n')
    ssh -t "$host" "sudo sh -c \"\$(echo $payload | base64 -d)\" allow-sudo.sh $*"
}

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "error: run with sudo" >&2
        exit 1
    fi
}

stop_revoke_timer() {
    systemctl stop "$REVOKE_UNIT.timer" "$REVOKE_UNIT.service" 2>/dev/null
    systemctl reset-failed "$REVOKE_UNIT.timer" "$REVOKE_UNIT.service" 2>/dev/null
}

grant() {
    duration=${1:-$DEFAULT_DURATION}
    if ! echo "$duration" | grep -Eq '^[0-9]+(s|sec|m|min|h|hr)?$'; then
        echo "error: invalid duration: $duration (e.g. 30m, 1h)" >&2
        exit 1
    fi
    target_user=${SUDO_USER:-}
    if [ -z "$target_user" ] || [ "$target_user" = root ]; then
        echo "error: run via sudo from your normal user account" >&2
        exit 1
    fi

    # Write to a temp file and validate first: a broken sudoers.d entry disables sudo entirely.
    # The temp file lives in sudoers.d (names containing "." are ignored by sudo) so the mv is atomic.
    tmp=$(mktemp /etc/sudoers.d/.allow-sudo.XXXXXX)
    echo "$target_user ALL=(ALL) NOPASSWD: ALL" > "$tmp"
    if ! visudo -cf "$tmp" >/dev/null; then
        rm -f "$tmp"
        echo "error: generated sudoers entry failed validation" >&2
        exit 1
    fi
    chmod 0440 "$tmp"
    chown root:root "$tmp"
    mv "$tmp" "$SUDOERS_FILE"

    echo "r $SUDOERS_FILE" > "$TMPFILES_FILE"

    stop_revoke_timer
    systemd-run --quiet --unit="$REVOKE_UNIT" --on-active="$duration" \
        /bin/rm -f "$SUDOERS_FILE"

    echo "granted: $target_user may sudo without password for $duration"
    status
}

revoke() {
    stop_revoke_timer
    rm -f "$SUDOERS_FILE"
    echo "revoked"
}

status() {
    if [ -e "$SUDOERS_FILE" ]; then
        echo "active: $(cat "$SUDOERS_FILE")"
        systemctl list-timers "$REVOKE_UNIT.timer" --no-pager | head -2
    else
        echo "inactive"
    fi
}

case "${1:-}" in
    -h|--help|"") usage ;;
    grant) require_root; grant "$2" ;;
    revoke) require_root; revoke ;;
    status) require_root; status ;;
    -*) usage >&2; exit 1 ;;
    *) run_on_host "$@" ;;
esac
