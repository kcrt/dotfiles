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
    echo "When only one argument is given, it is used as the message and the"
    echo "title falls back to the name of the running script (or \$OSNOTIFY_TITLE)."
    echo ""
    echo "Example of sourcing in another script:"
    echo "  source /path/to/$(basename "$0")"
    echo "  OSNotify \"Task Complete\" \"Your task has finished.\""
    exit 0
fi

source ${DOTFILES}/script/echo_color.sh

# Title used when a notification is sent with a message only. $OSNOTIFY_TITLE
# lets a script override it; otherwise the name of the running script is used.
# (ZSH_ARGZERO keeps the invoked script name even inside functions and sourced
# files, where zsh rewrites $0.)
function _OSNotify_title(){
	if [ -n "$OSNOTIFY_TITLE" ]; then
		printf '%s' "$OSNOTIFY_TITLE"
		return
	fi
	local name="${ZSH_ARGZERO:-$0}"
	name="${name##*/}"
	case "$name" in
		-*|zsh|bash|sh|"") name="shell" ;;
	esac
	printf '%s' "$name"
}

# Escape a string so that it can be embedded in an AppleScript string literal.
function _OSNotify_escape(){
	local s="$1"
	s="${s//\\/\\\\}"
	s="${s//\"/\\\"}"
	printf '%s' "$s"
}

# _OSNotify_split "$@" -> sets _OSNOTIFY_TITLE / _OSNOTIFY_MESSAGE
# Accepts either ("Title" "Message") or ("Message").
function _OSNotify_split(){
	if [ $# -ge 2 ]; then
		_OSNOTIFY_TITLE="$1"
		_OSNOTIFY_MESSAGE="$2"
	else
		_OSNOTIFY_TITLE="$(_OSNotify_title)"
		_OSNOTIFY_MESSAGE="$1"
	fi
}

function OSNotify(){
	local _OSNOTIFY_TITLE _OSNOTIFY_MESSAGE
	_OSNotify_split "$@"
	if command -v growlnotify >/dev/null 2>&1; then
		growlnotify -t "$_OSNOTIFY_TITLE" -m "$_OSNOTIFY_MESSAGE" >/dev/null 2>/dev/null
	elif [[ "$OSTYPE" = darwin* ]]; then
		echo "display notification \"$(_OSNotify_escape "$_OSNOTIFY_MESSAGE")\" with title \"$(_OSNotify_escape "$_OSNOTIFY_TITLE")\"" | osascript
	fi
	echo_aqua "$_OSNOTIFY_TITLE: $_OSNOTIFY_MESSAGE"
}

function OSError(){
	local _OSNOTIFY_TITLE _OSNOTIFY_MESSAGE
	_OSNotify_split "$@"
	if command -v growlnotify >/dev/null 2>&1; then
		growlnotify -p High -t "$_OSNOTIFY_TITLE" -m "$_OSNOTIFY_MESSAGE" >/dev/null 2>/dev/null
	elif [[ "$OSTYPE" = darwin* ]]; then
		echo "display notification \"$(_OSNotify_escape "$_OSNOTIFY_MESSAGE")\" with title \"$(_OSNotify_escape "$_OSNOTIFY_TITLE")\" subtitle \"***** ERROR *****\"" | osascript
	fi
	echo_red "$_OSNOTIFY_TITLE: $_OSNOTIFY_MESSAGE"
}
