#!/bin/bash

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

source ~/etc/script/OSNotify.sh

strtime=`date "+%H:%M"`

OSNotify "Time signal" "It's $strtime now!"
