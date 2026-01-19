#!/bin/bash

# notify to #develop channlel
eval "$(gpg --batch --no-tty -d ~/dotfiles/secrets/secrets.sh.asc 2>/dev/null)"
curl -X POST --data-urlencode "payload={\"channel\": \"#develop\", \"username\": \"console\", \"text\": \"$1\", \"icon_emoji\": \":ghost:\"}" "$SLACK_MY_URL"
