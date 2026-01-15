#
#	010-paths.zsh
#		Homebrew setup and PATH configuration
#

# ----- homebrew
# check arch to determine place of homebrew
if [[ "$OSTYPE" = darwin* ]]; then
	if [[ "$(uname -m)" = "arm64" ]]; then
		export BIN_HOMEBREW="/opt/homebrew/bin/brew"
	elif [[ "$(uname -m)" = "x86_64" ]]; then
		export BIN_HOMEBREW="/usr/local/bin/brew"
	fi
	alias brew="$BIN_HOMEBREW"

	# Set up Homebrew environment early (needed for sheldon and other tools)
	unset HOMEBREW_SHELLENV_PREFIX # dirty hack to prevent duplicate PATH entries
	eval $($BIN_HOMEBREW shellenv)

	# Load homebrew completions early to avoid conflicts
	# Cache brew prefix to avoid multiple calls
	local brew_prefix="$($BIN_HOMEBREW --prefix)"
	if [[ -d "$brew_prefix/share/zsh/site-functions" ]]; then
		FPATH="$brew_prefix/share/zsh/site-functions:${FPATH}"
	fi
fi

# Add ~/.local/bin to PATH
if [[ -d "$HOME/.local/bin" ]]; then
	typeset -U path PATH
	path=($path "$HOME/.local/bin")
fi

# ----- パス
typeset -U path PATH
# Add paths only if they exist
[[ -d "$HOME/.deno/bin" ]] && path=("$HOME/.deno/bin" $path)
[[ -n "$GOPATH" && -d "$GOPATH/bin" ]] && path=($path "$GOPATH/bin")
[[ -d "$HOME/.cargo/bin" ]] && path=($path "$HOME/.cargo/bin")
[[ -d "/snap/bin" ]] && path=($path "/snap/bin")
[[ -d "$HOME/bin" ]] && path=($path "$HOME/bin")
