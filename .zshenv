
if [ $BENCHMARK_ZSHRC ]; then
	zmodload zsh/zprof && zprof
fi

if [ -d /workspaces/.codespaces/.persistedshare/dotfiles ]; then
	# for GitHub Codespaces
	export DOTFILES="/workspaces/.codespaces/.persistedshare/dotfiles"
else
	export DOTFILES="${HOME}/dotfiles"
fi

export GOPATH="$HOME/go"
