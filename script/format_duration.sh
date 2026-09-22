#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  format_duration.sh
#         USAGE:  source ${DOTFILES}/script/format_duration.sh
#   DESCRIPTION:  Turn a number of seconds into something readable in a log.
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

# format_duration <seconds> -> "42s", "13m30s", "3h14m55s"
#
# Hours are spelled out because a maintenance step and an audio file are both
# routinely longer than an hour, and "194m55s" makes the reader do the division.
# A fractional argument ("39253.498813", as ffprobe reports a duration) is
# truncated, and anything unparseable comes back as "unknown".
function format_duration(){
	local sec="${1%%.*}"
	case "$sec" in
		''|*[!0-9]*) printf 'unknown\n'; return 1 ;;
	esac
	if [ "$sec" -ge 3600 ]; then
		printf '%dh%dm%ds\n' "$((sec / 3600))" "$(((sec % 3600) / 60))" "$((sec % 60))"
	elif [ "$sec" -ge 60 ]; then
		printf '%dm%ds\n' "$((sec / 60))" "$((sec % 60))"
	else
		printf '%ds\n' "$sec"
	fi
}
