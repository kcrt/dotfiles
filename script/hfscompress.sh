#!/bin/sh

#===============================================================================
#
#          FILE:  hfscompress.sh
#
#         USAGE:  ./hfscompress.sh _file_or_folder_
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

source ~/etc/script/echo_color.sh
source ~/etc/script/miscs.sh

need_app ditto > /dev/null

if [ $# -ne 1 ]; then
	echo "$0 filename"
	exit
fi

du -hs "$1"
~/etc/script/ask.sh -n "$1 will be compressed. ok?"
if [ $? -ne 0 ]; then
	echo "canceled."
	exit
fi

mv "$1" "$1_org"
ditto --hfsCompression "$1_org" "$1"
du -hs "$1"
echo "$1 was compressed."
~/etc/script/ask.sh -n "remove original?"
if [ $? -ne 0 ]; then
	echo "canceled."
	exit
fi
rm -R "$1_org"
