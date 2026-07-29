#!/bin/sh

if [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ "$#" = 0 ]; then
    echo "Usage: $(basename "$0") [-t <title>] [-p <priority>] [-U <url>] <message>"
    echo "Sends a push notification to iPhone via Pushover."
    echo "Reads the message from stdin if <message> is '-'."
    echo ""
    echo "Options:"
    echo "    -t <title>     Notification title (default: hostname)"
    echo "    -p <priority>  -2=silent, -1=quiet, 0=normal(default), 1=high, 2=emergency"
    echo "                   -p 2 retries every 60s for up to 1h until acknowledged"
    echo "    -U <url>       Supplementary URL to attach to the notification"
    echo ""
    echo "Required environment variables (loaded from dotfiles secrets):"
    echo "    PUSHOVER_APP_LOCAL_TOKEN  Application token of the 'local' Pushover app"
    echo "    PUSHOVER_USER_KEY         Pushover user key"
    echo ""
    echo "Example: $(basename "$0") -t 'Backup' -p 1 'Nightly backup failed'"
    echo "         df -h | $(basename "$0") -t 'Disk usage' -"
    exit 0
fi

TITLE=$(hostname -s)
PRIORITY=0
URL=""

while getopts "t:p:U:" opt; do
    case "$opt" in
        t) TITLE=$OPTARG ;;
        p) PRIORITY=$OPTARG ;;
        U) URL=$OPTARG ;;
        *) echo "Run with --help for usage." >&2; exit 1 ;;
    esac
done
shift $((OPTIND - 1))

if [ "$#" = 0 ]; then
    echo "Error: no message given. Run with --help for usage." >&2
    exit 1
fi

if [ -z "$PUSHOVER_APP_LOCAL_TOKEN" ] || [ -z "$PUSHOVER_USER_KEY" ]; then
    echo "Error: PUSHOVER_APP_LOCAL_TOKEN and PUSHOVER_USER_KEY must be set." >&2
    echo "They are loaded from the dotfiles secrets on shell startup;" >&2
    echo "start a new shell if you have just added them." >&2
    exit 1
fi

if [ "$1" = "-" ]; then
    MESSAGE=$(cat)
else
    MESSAGE=$*
fi

if [ -z "$MESSAGE" ]; then
    echo "Error: message is empty." >&2
    exit 1
fi

set -- --data-urlencode "token=$PUSHOVER_APP_LOCAL_TOKEN" \
       --data-urlencode "user=$PUSHOVER_USER_KEY" \
       --data-urlencode "title=$TITLE" \
       --data-urlencode "message=$MESSAGE" \
       --data-urlencode "priority=$PRIORITY"

# Emergency priority is rejected unless retry/expire are given.
if [ "$PRIORITY" = "2" ]; then
    set -- "$@" --data-urlencode "retry=60" --data-urlencode "expire=3600"
fi

if [ -n "$URL" ]; then
    set -- "$@" --data-urlencode "url=$URL"
fi

RESPONSE=$(curl -s --max-time 20 "$@" https://api.pushover.net/1/messages.json)

if echo "$RESPONSE" | grep -q '"status":1'; then
    exit 0
fi

echo "Error: Pushover rejected the request." >&2
echo "$RESPONSE" >&2
exit 1
