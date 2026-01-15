#
#	070-plugins.zsh
#		Sheldon, zoxide, and plugin configuration
#

# Skip all plugin loading when in Claude Code
[[ -n "$CLAUDECODE" ]] && return 0

# ----- sheldon (plugin manager)
if command -v sheldon &> /dev/null; then
	eval "$(sheldon source)"
else
	echo_warn "Please install sheldon for zsh plugins: https://sheldon.cli.rs/Installation.html"
	echo_warn "Use brew install sheldon (macOS) or cargo binstall sheldon (Linux)."
	function abbrev-alias(){
		# skip this command
	}
fi

# ----- zoxide (smarter cd command)
if command -v zoxide &> /dev/null; then
    eval "$(zoxide init zsh --cmd cd)"
	# --cmd cd: make zoxide override cd command (same as `alias cd='zoxide`, but better`)
else
	echo_warn "Warning: zoxide is not installed. Use brew or cargo to install zoxide."
fi
