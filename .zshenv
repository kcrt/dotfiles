if [ -d /workspaces/.codespaces/.persistedshare/dotfiles ]; then
	export DOTFILES="/workspaces/.codespaces/.persistedshare/dotfiles"
else
	export DOTFILES="${HOME}/dotfiles"
fi

export GOPATH="$HOME/go"

