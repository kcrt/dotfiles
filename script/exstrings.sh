#!/bin/zsh

#===============================================================================
#
#          FILE:  exstrings.sh
#
#         USAGE:  ./exstrings.sh FILENAME
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#		supported filetype;
#			Office: docx, pptx
#			Archive: zip, rar, lzh, 
#
#===============================================================================

if [[ "${1:e}" = "pptx" ]]; then
	unzip -p $1 "docProps/core.xml" | sed -e 's/<[^>]*>//g'
	for file in `zip -sf $1 | grep "ppt/slides/slide" | sed -e "s/ppt\/slides\/slide//" | sed -e "s/\.xml//" | sort -n`; do
		echo "----- Slide $file -----" 
			unzip -p $1 "ppt/slides/slide$file.xml" | sed -e 's/<\/a:p>/\
/g' | sed -e 's/<[^>]*>//g'
		echo ""
	done
elif [[ "${1:e}" = "docx" ]]; then
	if [[ -x =textutil ]]; then
		textutil -convert txt -stdout "$1"
	else
		unzip -p $1 "docProps/core.xml" | sed -e 's/<[^>]*>//g'
		unzip -p $1 "word/document.xml" | sed -e 's/<\/w:p>//g'| sed -e 's/<[^>]*>//g'
	fi
elif [[ "${1:e}" = "rtf" || "${1:e}" = "doc" ]]; then
	if [[ -x =textutil ]]; then
		textutil -convert txt -stdout "$1"
	else
		cat "$1"
	fi
elif [[ "${1:e}" = "zip" || "${1:e}" = "lzh" || "{$1:e" = "rar" ]]; then
	if [[ ! -x als ]]; then
		echo "als not found!"
	fi
	als $1
fi
