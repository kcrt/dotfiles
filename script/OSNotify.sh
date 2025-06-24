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

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: source $(basename "$0")"
    echo "This script provides functions for sending desktop notifications."
    echo "It is intended to be sourced by other scripts, not run directly."
    echo ""
    echo "Functions available after sourcing:"
    echo "  OSNotify \"Title\" \"Message\"   - Shows a standard notification."
    echo "  OSError \"Title\" \"Error Message\" - Shows an error notification."
    echo ""
    echo "Example of sourcing in another script:"
    echo "  source /path/to/$(basename "$0")"
    echo "  OSNotify \"Task Complete\" \"Your task has finished.\""
    exit 0
fi

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
