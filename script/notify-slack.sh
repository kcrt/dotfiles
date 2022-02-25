#!/bin/sh

# notify to #develop channlel
source "~/dotfiles/no_git/secrets.sh"

curl -X POST --data-urlencode "payload={\"channel\": \"#develop\", \"username\": \"console\", \"text\": \"$1\", \"icon_emoji\": \":ghost:\"}" "$SLACK_MY_URL"
