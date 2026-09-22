#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  nfd_safe_glob.sh
#         USAGE:  source ${DOTFILES}/script/nfd_safe_glob.sh
#   DESCRIPTION:  List files without letting zsh rewrite their names.
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

# zsh 5.9 on macOS hands back composed (NFC) names from a glob, whatever is
# actually on disk. APFS hides this because it matches either form on lookup,
# but the QNAP's SMB shares store the decomposed (NFD) form and match nothing
# else. A globbed name holding a decomposable character - "が" is か + U+3099
# there - therefore fails every [[ -e ]], mv and command argument that follows:
# the file is listed, and then unreachable.
#
#     zsh:  for i in *.m4a  ->  ...きょうすがねる.m4a  (e3 81 8c, NFC)  -> missing
#     find: -print0         ->  ...きょうすがねる.m4a  (e3 81 8b e3 82 99) -> found
#
# find(1) passes the bytes through untouched and read(1) keeps them, so build
# the list from there whenever the directory may live on a network share.
#
# nfd_safe_glob <array name> <directory> <name pattern>
# Fills the named array with the matching regular files, sorted by byte value.
# The array is emptied when nothing matches; a missing directory is not an
# error here, it simply matches nothing.
function nfd_safe_glob(){
	local -a matches=()
	local file
	while IFS= read -r -d '' file; do
		matches+=("$file")
	done < <(find "$2" -maxdepth 1 -type f -name "$3" -print0 2>/dev/null | LC_ALL=C sort -z)
	set -A "$1" "${matches[@]}"
}
