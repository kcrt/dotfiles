#
# 703-aliases-external.zsh
#   Conditional loading of external tool aliases
#

# ============================================================================
# thefuck
# ============================================================================

if [[ -x "$(command -v thefuck)" && -z "$THEFUCK_LOADED" ]]; then
	export THEFUCK_LOADED=1
	eval "$(thefuck --alias)"
fi

# ============================================================================
# croc (via Docker if not installed)
# ============================================================================

if ! command -v croc &> /dev/null; then
	function croc() {
		docker run -it --rm -w "$(pwd)" -v "$(pwd):$(pwd)" thecatlady/croc "$@"
	}
fi

# ============================================================================
# dstat
# ============================================================================

if command -v dstat &> /dev/null; then
	alias dstat='sudo dstat -t -cl --top-cpu -m -d --top-io -n'
fi

# ============================================================================
# ghidra
# ============================================================================

if [[ -f "/opt/homebrew/opt/ghidra/libexec/ghidraRun" ]]; then
	alias ghidra='/opt/homebrew/opt/ghidra/libexec/ghidraRun'
fi

# ============================================================================
# lms (LM Studio CLI)
# ============================================================================

# 標準パスに symlink されない実体バイナリなので alias で解決する。
# インストーラは .zshrc に絶対パスの PATH を追記してくるが、それは削除済み。
if [[ -x "$HOME/.lmstudio/bin/lms" ]]; then
	alias lms="$HOME/.lmstudio/bin/lms"
fi
