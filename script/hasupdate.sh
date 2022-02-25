#!/bin/sh

#===============================================================================
#
#          FILE:  hasupdate.sh
#
#         USAGE:  ./hasupdate.sh
#
#   DESCRIPTION:
#
#===============================================================================


NUM=0
if [ -x /usr/bin/aptitude ]; then
	NUM=`aptitude search '~U' | wc -l`
elif [ -x /usr/local/bin/brew ]; then
	#brew update & 2>&1 >/dev/null
	#NUM=`brew outdated | wc -l`
elif [ -x /opt/local/bin/port ]; then
	NUM=`port list outdated | wc -l`
fi

if [ $NUM -le 0 ]; then
	echo ""
else
	echo "$NUM updates."
fi
