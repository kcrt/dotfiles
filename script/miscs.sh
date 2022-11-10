#!/bin/bash

function if_error(){
	# usage: if_error "Cannot execute command"
	if [[ $? -ne 0 ]]; then
		echo_red $1
		exit
	fi
}

function need_app(){
	# usage: need_app "git"

	if [[ ! -x `which $1` ]]; then
		echo_red "'$1' not found!"
		exit
	else
		echo_green "'$1' found."
	fi

}
