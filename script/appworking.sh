#!/bin/bash

#===============================================================================
#
#          FILE:  appworking.sh
#
#         USAGE:  ./appworking.sh app1 app1str app2 app2str
#
#   DESCRIPTION:  Checks if the given apps are running and returns a string
#
#===============================================================================

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0") app1 app1str app2 app2str ..."
    echo "Checks if the given apps are running and returns a string indicating which are active."
    echo "Example: $(basename "$0") \"Google Chrome\" \"Chrome\" \"Terminal\" \"Term\""
	echo "Returns: [Chrome][Term] if both apps are running."
    exit 0
fi

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
