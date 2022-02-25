#!/usr/bin/env zsh

TARGET=`cat ~/VolumeMain.txt | grep "Main/comics" | sed "s|/mnt/DroboFS/Shares/Main|/Volumes/Main|" | grep -v ".zip" | grep -v ".rar" | /Users/kcrt/etc/script/mgrep.sh "$1" | peco`
if [ -n "$TARGET" ]; then
	open "$TARGET"
fi
