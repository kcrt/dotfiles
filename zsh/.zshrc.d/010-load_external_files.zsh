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
for f in OSNotify.sh echo_color.sh miscs.sh; do
	if [[ ! -f "${DOTFILES}/script/${f}" ]]; then
		printf '\033[31m*** Missing: %s/script/%s (check DOTFILES path)\033[0m\n' "${DOTFILES}" "${f}" >&2
		return 1
	fi
	source "${DOTFILES}/script/${f}"
done
