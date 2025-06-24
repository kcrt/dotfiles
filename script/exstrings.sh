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

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0") <FILENAME>"
    echo "Extracts text content from various file types."
    echo ""
    echo "Supported file types (extensions):"
    echo "  pptx, docx, rtf, doc, pdf, zip, lzh, rar"
    echo ""
    echo "Requirements depend on the file type:"
    echo "  - Office files (pptx, docx, rtf, doc): 'textutil' (macOS) or 'unzip' and 'sed'."
    echo "  - PDF: 'pdftotext' (from poppler-utils)."
    echo "  - Archives (zip, lzh, rar): 'als' (Archive Listing Service)."
    exit 0
fi

if [ -z "$1" ]; then
    echo "Error: No filename specified."
    echo "Usage: $(basename "$0") <FILENAME>"
    echo "For more help, run: $(basename "$0") --help"
    exit 1
fi

# set EXT to lower case extention
# EXT="${1:e}"
EXT="${1:e:l}"

# use case to determine the file type


if [[ "$EXT" = "pptx" ]]; then
	unzip -p $1 "docProps/core.xml" | sed -e 's/<[^>]*>//g'
	for file in `zip -sf $1 | grep "ppt/slides/slide" | sed -e "s/ppt\/slides\/slide//" | sed -e "s/\.xml//" | sort -n`; do
		echo "----- Slide $file -----" 
			unzip -p $1 "ppt/slides/slide$file.xml" | sed -e 's/<\/a:p>/\
/g' | sed -e 's/<[^>]*>//g'
		echo ""
	done
elif [[ "$EXT" = "docx" ]]; then
	if [[ -x =textutil ]]; then
		textutil -convert txt -stdout "$1"
	else
		unzip -p $1 "docProps/core.xml" | sed -e 's/<[^>]*>//g'
		unzip -p $1 "word/document.xml" | sed -e 's/<\/w:p>//g'| sed -e 's/<[^>]*>//g'
	fi
elif [[ "$EXT" = "rtf" || "${1:e}" = "doc" ]]; then
	if [[ -x =textutil ]]; then
		textutil -convert txt -stdout "$1"
	else
		cat "$1"
	fi
elif [[ "$EXT" = "pdf" ]]; then
	if [[ -x =pdftotext ]]; then
		pdftotext "$1" - | sed -e 's//\n-----\n/g'
	else
		echo "pdftotext not found!"
	fi
elif [[ "$EXT" = "zip" || "$EXT" = "lzh" || "$EXT" = "rar" ]]; then
	if [[ ! -x als ]]; then
		echo "als not found!"
	fi
	als $1
else
	# not supported
	echo "Unsupported file type."
fi
