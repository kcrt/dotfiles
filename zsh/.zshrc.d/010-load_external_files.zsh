#
#	010-load_external_files.zsh
#		Load external utility scripts
#

# ----- load external files
# Ensure DOTFILES is defined (should be set in .zshenv, but provide fallback)
if [[ -z "$DOTFILES" ]]; then
	echo "*** DOTFILES not set, using default path. ***"
	export DOTFILES="${HOME}/dotfiles"
fi
source ${DOTFILES}/script/OSNotify.sh
source ${DOTFILES}/script/echo_color.sh
source ${DOTFILES}/script/miscs.sh
