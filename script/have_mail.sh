#!/bin/sh

#===============================================================================
#
#          FILE:  FILENAME_GOES_HERE.sh
#
#         USAGE:  ./FILENAME_GOES_HERE.sh
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

NUMMAIL=$(mail -H 2>&1 | grep "^.[UN]" | wc -l)

if [ $NUMMAIL = 0 ]; then
	echo ""
else
	echo " 📧"
fi
