#
#	010-load_external_files.zsh
#		Load external utility scripts
#

# ----- load external files
if [[ -z "$DOTFILES" ]]; then
	echo "DOTFILES is not defined. Please define DOTFILES in .zshenv"
	return 1
fi
source ${DOTFILES}/script/OSNotify.sh
source ${DOTFILES}/script/echo_color.sh
source ${DOTFILES}/script/miscs.sh
