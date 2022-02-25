#!/bin/bash

#===============================================================================
#
#          FILE:  appworking.sh
#
#         USAGE:  ./appworking.sh app1 app1str app2 app2str
#
#   DESCRIPTION:
#
#       OPTIONS:  ---
#  REQUIREMENTS:  ---
#          BUGS:  ---
#         NOTES:  ---
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#      REVISION:  $Id$
#
#===============================================================================

ps aux | grep -v $0 > /tmp/psaux
while [ "$1" != "" ]; do
	app=$1
	appstr=$2
	cat /tmp/psaux | grep "$app" >> /dev/null
	if [[ $? -eq 0 ]]; then
		retstr="$retstr[$appstr]"
	fi
	shift; shift;
done
rm /tmp/psaux

echo -n $retstr
