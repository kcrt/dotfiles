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
		# Use timeout to prevent hanging if pinentry can't display
		# --batch fails fast if passphrase isn't cached in agent
		if command -v timeout &> /dev/null; then
			eval "$(timeout 2 $GPG_BIN --batch -d ${DOTFILES}/secrets/secrets.sh.asc 2>/dev/null)"
		else
			eval "$($GPG_BIN --batch -d ${DOTFILES}/secrets/secrets.sh.asc 2>/dev/null)"
		fi
	else
		echo_warn "GPG not found. Cannot load encrypted secrets."
	fi
	unset GPG_BIN
	if [ -z "$SECRET_KEYS_SUCCESSFULLY_LOADED" ]; then
		echo_warn "Warning: Secret keys not loaded. Check setup and private GPG keys."
	fi
else
	echo_info "No encrypted secrets file found at ${DOTFILES}/secrets/secrets.sh.asc"
	echo_info "(You may need 'git submodule update --init --recursive' to fetch it.)"
fi
