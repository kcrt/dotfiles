#
#	020-load_secrets.zsh
#		Load encrypted secrets using GPG
#


# Set GPG_TTY for proper terminal handling
# In non-TTY environments (like Claude Code), GPG will use the agent
current_tty=$(tty 2>/dev/null)
if [[ "$current_tty" != "not a tty" && -n "$current_tty" ]]; then
	export GPG_TTY=$current_tty
fi

# Load encrypted secrets if available
if [ -f ${DOTFILES}/secrets/secrets.sh.asc ]; then
	if [[ -x "/opt/homebrew/bin/gpg" ]]; then
		GPG_BIN="/opt/homebrew/bin/gpg"
	elif [[ -x "/usr/local/bin/gpg" ]]; then
		GPG_BIN="/usr/local/bin/gpg"
	elif command -v gpg &> /dev/null; then
		GPG_BIN="gpg"
	else
		GPG_BIN=""
	fi

	if [[ -n "$GPG_BIN" ]]; then
		eval "$($GPG_BIN -d ${DOTFILES}/secrets/secrets.sh.asc 2>/dev/null)"
	fi
	unset GPG_BIN
fi
if [ -z "$SECRET_KEYS_SUCCESSFULLY_LOADED" ]; then
	echo_warn "Warning: Secret keys not loaded. Encrypted secrets.sh.asc file may be missing or GPG is not installed."
fi
