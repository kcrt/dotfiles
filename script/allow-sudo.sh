#!/bin/sh

# Temporarily allow passwordless sudo (e.g. for non-interactive sudo over ssh), with automatic expiry.
# MODIFIES the system: writes /etc/sudoers.d/zz-allow-sudo-temp and /etc/tmpfiles.d/allow-sudo.conf.
# Target: Linux hosts with systemd (Ubuntu). Always invoked as "allow-sudo.sh HOST MODE"; for a remote
# HOST this script is sent over ssh (the host need not have it), for localhost it is run via sudo.

SUDOERS_FILE=/etc/sudoers.d/zz-allow-sudo-temp
TMPFILES_FILE=/etc/tmpfiles.d/allow-sudo.conf
REVOKE_UNIT=allow-sudo-revoke
DEFAULT_DURATION=30m

usage() {
    cat <<EOF
Usage: $(basename "$0") HOST MODE [DURATION]
       HOST: an ssh destination (e.g. boron.local), or localhost for this machine
       MODE: grant [DURATION] | revoke | status

Temporarily grants NOPASSWD sudo to your user on HOST. Do not run this script itself with sudo;
it calls sudo on HOST (you type the sudo password there once for grant).

  grant [DURATION]  Allow passwordless sudo for DURATION (systemd time span:
                    30m, 1h, 90min ...; default: $DEFAULT_DURATION). Granting again
                    resets the expiry.
  revoke            Remove the permission immediately.
  status            Show whether the permission is active and when it expires.

Expiry is enforced twice:
  - a transient systemd timer ($REVOKE_UNIT) deletes $SUDOERS_FILE, and
  - $TMPFILES_FILE deletes it at boot (transient timers do not survive reboot).

The local copy of this script is what runs on HOST, so HOST's own dotfiles may be old or absent.
Examples: $(basename "$0") boron.local grant 1h / $(basename "$0") localhost status
EOF
}

run_on_host() {
    host=$1
    shift
    case "${1:-}" in
        grant|revoke|status) ;;
        *) usage >&2; exit 1 ;;
    esac
    if [ "$host" = localhost ]; then
        exec sudo sh -c "$(cat "$0")" allow-sudo.sh --as-root "$@"
    fi
    # Arguments are interpolated into the remote shell command, so allow only plain tokens.
    for arg in "$@"; do
        if ! echo "$arg" | grep -Eq '^[A-Za-z0-9]+$'; then
            echo "error: invalid argument: $arg" >&2
            exit 1
        fi
    done
    payload=$(base64 < "$0" | tr -d '\n')
    ssh -t "$host" "sudo sh -c \"\$(echo $payload | base64 -d)\" allow-sudo.sh --as-root $*"
}

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "error: --as-root must run as root (use: allow-sudo.sh HOST MODE)" >&2
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

# --as-root MODE: internal entry point that run_on_host invokes via sudo on HOST.
case "${1:-}" in
    -h|--help|"") usage ;;
    --as-root)
        require_root
        case "${2:-}" in
            grant) grant "$3" ;;
            revoke) revoke ;;
            status) status ;;
            *) usage >&2; exit 1 ;;
        esac
        ;;
    -*|grant|revoke|status) usage >&2; exit 1 ;;
    *) run_on_host "$@" ;;
esac
