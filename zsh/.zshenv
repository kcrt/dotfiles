
if [ $BENCHMARK_ZSHRC ]; then
	zmodload zsh/zprof && zprof
fi

if [ -d /workspaces/.codespaces/.persistedshare/dotfiles ]; then
	# for GitHub Codespaces
	export DOTFILES="/workspaces/.codespaces/.persistedshare/dotfiles"
else
	export DOTFILES="${HOME}/dotfiles"
fi

if [ -d "${DOTFILES}/sheldon" ]; then
	export SHELDON_CONFIG_DIR="${DOTFILES}/sheldon"
fi

export GOPATH="$HOME/go"

# Activate mise for all shells (including non-interactive)
if command -v mise &> /dev/null; then
	eval "$(mise activate zsh)"
fi
