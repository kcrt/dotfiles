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
