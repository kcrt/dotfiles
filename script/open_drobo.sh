#!/usr/bin/env zsh

TARGET=`cat ~/VolumeMain.txt | sed "s|/mnt/DroboFS/Shares/|/Volumes/|" | grep -v "[^/]*\..*$" | /Users/kcrt/dotfiles/script/mgrep.sh "$1" | peco`
if [ -n "$TARGET" ]; then
	open "$TARGET"
fi
