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

# `source` hands the caller's positional parameters to this file, so looking at
# $1 alone made every script that sources it print the help below and exit 0 as
# soon as that script itself was called with --help - maintain.sh and all of its
# routines included. Only answer for --help when this file is the one that was
# started: zsh records the nesting in $ZSH_EVAL_CONTEXT, where a "file"
# component means a `source`, and bash keeps the started script in $0 while
# $BASH_SOURCE follows the current file. Any other shell simply does not
# print it.
_OSNotify_is_run_directly(){
	if [ -n "$ZSH_EVAL_CONTEXT" ]; then
		# One component per level, including the ":shfunc" of this very
		# function, so match the "file" rather than the whole string.
		case "$ZSH_EVAL_CONTEXT" in
			*file*) return 1 ;;
			*)      return 0 ;;
		esac
	elif [ -n "$BASH_SOURCE" ]; then
		[ "$BASH_SOURCE" = "$0" ]
	else
		return 1
	fi
}

if _OSNotify_is_run_directly && { [ "$1" = "--help" ] || [ "$1" = "-h" ]; }; then
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

# --- failure counting for maintenance routines --------------------------------
# A routine that logs an error and then ends on a successful command still
# reports success to its caller, which is how a failing 'brew upgrade' kept
# being recorded as a finished step. count_failure() records the problem and
# lets the routine carry on with its remaining work; routine_exit_status()
# turns the tally into an exit code at the end of the script.
ROUTINE_FAILURES=0

function count_failure(){
	OSError "$1"
	ROUTINE_FAILURES=$((ROUTINE_FAILURES + 1))
	return 0
}

function routine_exit_status(){
	if [ "$ROUTINE_FAILURES" -eq 0 ]; then
		return 0
	fi
	OSError "$ROUTINE_FAILURES step(s) of this routine failed."
	return 1
}

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
