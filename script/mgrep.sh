#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  mgrep.sh
#
#   DESCRIPTION:  grep with cmigemo
#
#===============================================================================

if [ $# -eq 0 ]; then
	echo "example: ls | mgrep misoshiru" 
	echo "which is to grep -E (ﾐｿｼﾙ|ミソシル|味噌汁|みそしる|ｍｉｓｏｓｈｉｒｕ|misoshiru)"
	exit
elif [ $# -eq 1 ]; then
	if [ "$(uname)" = "Darwin" ]; then
		iconv -c -f UTF-8-MAC -t UTF-8 | grep --color=auto -E `cmigemo -d /opt/homebrew/Cellar/cmigemo/*/share/migemo/utf-8/migemo-dict -w "$1"`
	else
		grep --color=auto -E `cmigemo -d /usr/share/cmigemo/utf-8/migemo-dict -w "$1"`
	fi
fi


