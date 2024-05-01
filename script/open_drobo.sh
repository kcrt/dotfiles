#!/usr/bin/env zsh

TARGET=`cat ~/DroboFileList.txt | grep -v "[^/]*\..*$" | /Users/kcrt/dotfiles/script/mgrep.sh "$1" | peco`
if [ -n "$TARGET" ]; then
	echo "opening $TARGET"
	open "$TARGET"
fi
