#!/usr/bin/env zsh

TARGET=`cat ~/QnapFileList.txt | grep -v "[^/]*\..*$" | sed 's/^\/share/\/Volumes/g' | /Users/kcrt/dotfiles/script/mgrep.sh "$1" | peco`
if [ -n "$TARGET" ]; then
	echo "opening $TARGET"
	open "$TARGET"
fi
