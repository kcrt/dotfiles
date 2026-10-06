#!/bin/bash

# notify to #develop channlel
# Secrets come from with-secret: re-run this script through it (Touch ID) if unset.
[ -n "${SLACK_MY_URL:-}" ] || exec with-secret SLACK_MY_URL -- "$0" "$@"
curl -X POST --data-urlencode "payload={\"channel\": \"#develop\", \"username\": \"console\", \"text\": \"$1\", \"icon_emoji\": \":ghost:\"}" "$SLACK_MY_URL"
