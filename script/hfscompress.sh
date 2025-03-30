#!/bin/sh


source ~/dotfiles/script/echo_color.sh
source ~/dotfiles/script/miscs.sh

need_app ditto > /dev/null

if [ $# -ne 1 ]; then
	echo "$0 filename"
	exit
fi

du -hs "$1"
~/dotfiles/script/ask.sh -n "$1 will be compressed. ok?"
if [ $? -ne 0 ]; then
	echo "canceled."
	exit
fi

mv "$1" "$1_org"
ditto --hfsCompression "$1_org" "$1"
du -hs "$1"
echo "$1 was compressed."
~/dotfiles/script/ask.sh -n "remove original?"
if [ $? -ne 0 ]; then
	echo "canceled."
	exit
fi
rm -R "$1_org"
