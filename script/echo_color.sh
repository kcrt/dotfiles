#!/bin/sh

#===============================================================================
#
#          FILE:  echo_color.sh
#
#         USAGE:  source echo_color.sh
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

function echo_color(){

	echo -n "[$1m"
	shift
	echo "$@"
	echo -n "[0m"

}

function echo_black(){ echo_color "30" "$@"; }
function echo_brightblack(){ echo_color "01;30" "$@"; }
function echo_red(){ echo_color "31" "$@"; }
function echo_brightred(){ echo_color "01;31" "$@"; }
function echo_green(){ echo_color "32" "$@"; }
function echo_brightgreen(){ echo_color "01;32" "$@"; }
function echo_yellow(){ echo_color "33" "$@"; }
function echo_brightyellow(){ echo_color "01;33" "$@"; }
function echo_blue(){ echo_color "34" "$@"; }
function echo_brightblue(){ echo_color "01;34" "$@"; }
function echo_mazenda(){ echo_color "35" "$@"; }
function echo_brightmazenda(){ echo_color "01;35" "$@"; }
function echo_aqua(){ echo_color "36" "$@"; }
function echo_brightaqua(){ echo_color "01;36" "$@"; }
function echo_white(){ echo_color "37" "$@"; }
function echo_brightwhite(){ echo_color "01;37" "$@"; }

function echo_error(){ echo_red "$@"; }
function echo_info(){ echo_aqua "$@"; }
function echo_ok(){ echo_green "$@"; }

function echo_colortest(){
	echo_black "black"
	echo_brightblack "brightblack"
	echo_red "red"
	echo_brightred "brightred"
	echo_green "green"
	echo_brightgreen "brightgreen"
	echo_yellow "yellow"
	echo_brightyellow "brightyellow"
	echo_blue "blue"
	echo_brightblue "brightblue"
	echo_mazenda "mazenda"
	echo_brightmazenda "brightmazenda"
	echo_aqua "aqua"
	echo_brightaqua "brightaqua"
	echo_white "white"
	echo_brightwhite "brightwhite"
}
