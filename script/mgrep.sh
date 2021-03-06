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
	exit
elif [ $# -eq 1 ]; then
	grep --color=auto -E `cmigemo -d /opt/homebrew/Cellar/cmigemo/*/share/migemo/utf-8/migemo-dict -w "$1"`   
fi


