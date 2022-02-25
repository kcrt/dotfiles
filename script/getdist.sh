#!/bin/sh

if [ -x /usr/bin/lsb_release ]; then
	/usr/bin/lsb_release -d | sed 's/Description:[\t ]*//'
elif [ -x /usr/bin/sw_vers ]; then
	echo "`sw_vers -productName` `sw_vers -productVersion` (`uname -m`)"
elif [ -x /bin/uname ]; then
	echo "`uname -sr` (`uname -m`)"
else
	echo "unknown"
fi
