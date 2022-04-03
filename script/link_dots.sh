#!/usr/bin/env bash

echo "Linking dotfiles..."
for file in ~/dotfiles/.*; do
	basename=`basename $file`
	if [ -f $file ] ; then
		[ -f ~/$basename ] && mv ~/$basename ~/$basename.init
		ln -s $file ~/$basename
	fi
done
