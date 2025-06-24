#!/bin/sh

#===============================================================================
#
#          FILE:  echo_color.sh
#
#         USAGE:  source echo_color.sh
#
#===============================================================================

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: source $(basename "$0")"
    echo "This script provides functions for echoing text in various ANSI colors."
    echo "It is intended to be sourced by other scripts, not run directly."
    echo ""
    echo "Example functions available after sourcing:"
    echo "  echo_red \"This is red\""
    echo "  echo_green \"This is green\""
    echo "  echo_blue \"This is blue\""
    echo "  echo_yellow \"This is yellow\""
    echo "  echo_aqua \"This is aqua\""
    echo "  echo_mazenda \"This is magenta\""
    echo "  echo_white \"This is white\""
    echo "  echo_black \"This is black\""
    echo "  echo_brightred, echo_brightgreen, etc. for bright versions."
    echo "  echo_error, echo_info, echo_ok for semantic coloring."
    echo "  echo_colortest - Displays a test of all available colors."
    echo ""
    echo "Example of sourcing in another script:"
    echo "  source /path/to/$(basename "$0")"
    echo "  echo_error \"Something went wrong!\""
    exit 0
fi

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
