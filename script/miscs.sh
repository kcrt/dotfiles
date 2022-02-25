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

function if_error(){
	if [[ $? -ne 0 ]]; then
		echo_red $1
		exit
	fi
}

function need_app(){

	if [[ ! -x `which $1` ]]; then
		echo_red "$1 not found!"
		exit
	else
		echo_green "$1 found."
	fi

}
