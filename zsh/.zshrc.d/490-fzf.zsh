#
#	490-fzf.zsh
#		fzf configuration and keybindings
#

# Skip fzf loading when in Claude Code
[[ -n "$CLAUDECODE" ]] && return 0

# ----- fzf setup
if command -v fzf &> /dev/null; then
	# Find fzf installation directory
	fzf_dir=""
	if [[ -d /opt/homebrew/opt/fzf/shell ]]; then
		fzf_dir="/opt/homebrew/opt/fzf/shell"
	elif [[ -d /usr/share/fzf ]]; then
		fzf_dir="/usr/share/fzf"
	elif [[ -d /usr/share/doc/fzf/examples ]]; then
		fzf_dir="/usr/share/doc/fzf/examples"
	fi

	# Source fzf keybindings and completion
	if [[ -n "$fzf_dir" ]]; then
		[[ -f "$fzf_dir/key-bindings.zsh" ]] && source "$fzf_dir/key-bindings.zsh"
		[[ -f "$fzf_dir/completion.zsh" ]] && source "$fzf_dir/completion.zsh"
	fi

	# fzf configuration
	export FZF_DEFAULT_OPTS='
		--height 40%
		--layout=reverse
		--border
		--cycle
		--info=inline
	'

	# Use fd for faster file listing if available
	if command -v fd &> /dev/null; then
		export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
		export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
		export FZF_ALT_C_COMMAND='fd --type d --hidden --follow --exclude .git'
	fi

	export FZF_CTRL_R_OPTS='
		--sort
		--exact
	'
	# Add preview to file widget
	export FZF_CTRL_T_OPTS='
		--preview "bat --color=always --line-range=:100 --style=numbers,changes {}"
		--preview-window right:60%:wrap
	'
	# Use Ctrl-X Ctrl-F (like vim!)
	bindkey -r '^T'
	bindkey '^X^F' fzf-file-widget

else
	echo_warn "Warning: fzf is not installed. Use brew|apt install fzf."
fi
