#!/bin/sh
#
#	get_secret.sh
#		Print one secret from the gpg-encrypted dotfiles secrets file.
#
#	The secrets are normally exported by zsh/.zshrc.d/020-load_secrets.zsh, but
#	that only runs for interactive shells. Non-interactive callers (cron jobs,
#	background agents, plain `sh -c`) have no secrets in their environment, so
#	they can use this helper to fetch a single value on demand instead.
#

if [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ "$#" = 0 ]; then
    echo "Usage: $(basename "$0") <NAME>"
    echo "Prints the value of one secret defined in the encrypted secrets file."
    echo ""
    echo "Looks up NAME in \${DOTFILES:-\$HOME/dotfiles}/secrets/secrets.sh.asc"
    echo "(decrypted with gpg --batch, so the passphrase must be cached in"
    echo "gpg-agent or supplied by pinentry). Prints nothing and exits non-zero"
    echo "when the secret is missing or decryption fails."
    echo ""
    echo "Prefer the exported environment variable when it is already set;"
    echo "this helper is the fallback for non-interactive shells."
    echo ""
    echo "Example: CLAUDE_ATMARK_KCRT_DOT_NET_PASSWORD=\$($(basename "$0") CLAUDE_ATMARK_KCRT_DOT_NET_PASSWORD)"
    exit 0
fi

NAME=$1
# Only shell-identifier characters, so the name can be pasted into sed safely.
case "$NAME" in
    "" | [0-9]* | *[!A-Za-z0-9_]*)
        echo "$(basename "$0"): invalid secret name: $NAME" >&2
        exit 2
        ;;
esac

SECRETS_FILE="${DOTFILES:-$HOME/dotfiles}/secrets/secrets.sh.asc"
if [ ! -f "$SECRETS_FILE" ]; then
    echo "$(basename "$0"): secrets file not found: $SECRETS_FILE" >&2
    exit 1
fi

for candidate in /opt/homebrew/bin/gpg /usr/local/bin/gpg gpg; do
    if command -v "$candidate" > /dev/null 2>&1; then
        GPG_BIN=$candidate
        break
    fi
done
if [ -z "$GPG_BIN" ]; then
    echo "$(basename "$0"): gpg not found" >&2
    exit 1
fi

# --batch fails fast instead of hanging when the passphrase is not cached.
PLAIN=$("$GPG_BIN" --batch -d "$SECRETS_FILE" 2> /dev/null)
if [ -z "$PLAIN" ]; then
    echo "$(basename "$0"): failed to decrypt $SECRETS_FILE" >&2
    echo "  Try: gpg -d $SECRETS_FILE   (to see the real error / cache the passphrase)" >&2
    exit 1
fi

# Take the last assignment so later overrides win, matching `eval` of the file.
# Two patterns instead of an optional group: BSD sed has no \? / \+ in BREs.
# Then strip one layer of single or double quotes.
VALUE=$(printf '%s\n' "$PLAIN" \
    | sed -n \
        -e "s/^[[:space:]]*${NAME}=//p" \
        -e "s/^[[:space:]]*export[[:space:]][[:space:]]*${NAME}=//p" \
    | tail -n 1 \
    | sed -e "s/^'\(.*\)'\$/\1/" -e 's/^"\(.*\)"$/\1/')

if [ -z "$VALUE" ]; then
    echo "$(basename "$0"): secret not found in $(basename "$SECRETS_FILE"): $NAME" >&2
    exit 1
fi

printf '%s\n' "$VALUE"
