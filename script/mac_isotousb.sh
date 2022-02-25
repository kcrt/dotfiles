#!/bin/sh

#===============================================================================
#
#          FILE:  mac_isotousb.sh
#
#         USAGE:  ./mac_isotousb.sh ISOFILE USBDEV
#
#   DESCRIPTION:
#
#       OPTIONS:  ---
#  REQUIREMENTS:  ---
#          BUGS:  ---
#         NOTES:  ---
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ~/etc/script/echo_color.sh
source ~/etc/script/miscs.sh

# DIST=`~/etc/script/getdist.sh`
# if [ "$DIST" != "Mac*" ]; then
# 	echo_error "This program cannot be run in non-darwin OS."
# 	exit
# fi

if [ $# -ne 2 ]; then
	echo "$0 ISOFILE USBDEV"
	/usr/sbin/diskutil list
	exit
fi

PATH="$PATH:/usr/sbin/"

need_app hdiutil
need_app diskutil

echo "Going to Write $1 to $2."
echo_error "***** WARNING *****"
~/etc/script/ask.sh -n "Files on $2 will be erased. ok?"

if [ $? -ne 0 ]; then
	exit
fi

echo_info "Converting iso to img."
hdiutil convert -format UDRW -o $1_converted.img $1

echo_info "Unmounting disk $2."
sudo /usr/sbin/diskutil unmountDisk $2

echo_info "Writting image $1 to $2."
sudo dd if=$1_converted.img.dmg of=$2 bs=1m

echo_info "Ejecting disk $2."
sudo /usr/sbin/diskutil eject $2


echo_ok "***** All process finished *****"
