#!/usr/bin/env zsh

if [ $# -eq 0 ]; then
	echo "$0 file_to_convert.md"
	exit
fi

filename="$1"
pandoc $filename -t docx --reference-doc $HOME/etc/template/template.docx --toc --highlight-style=zenburn -o ${filename:r}.docx
