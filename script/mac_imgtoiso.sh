#!/bin/sh

if [ $# -ne 1 ]; then
	echo "$0 imgfile"
	exit
fi

hdiutil makehybrid -iso -joliet -o ${1%.*}.iso $1 
