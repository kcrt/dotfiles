#!/bin/bash

#===============================================================================
#
#          FILE:  OSNotify.sh
#
#         USAGE:  (include this file)
#
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/echo_color.sh

function OSNotify(){
	if [[ -x `which growlnotify` ]]; then
		growlnotify -t $1 -m "$2" >/dev/null 2>/dev/null
	elif [[ "$OSTYPE" = darwin* ]]; then
		echo "display notification \"$2\" with title \"$1\"" |osascript
	fi
	echo_aqua "$1: $2"
}

function OSError(){
	if [[ -x `which growlnotify` ]]; then
		growlnotify -p High -t $1 -m "$2" >/dev/null 2>/dev/null
	elif [[ "$OSTYPE" = darwin* ]]; then
		echo "display notification \"$2\" with title \"$1\" subtitle \"***** ERROR *****\"" |osascript
	fi
	echo_red "$1: $2"
}
