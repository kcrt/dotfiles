#!/bin/zsh

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Recursively finds RAR files (*.rar) in the current directory and subdirectories,"
    echo "converts them to ZIP files, and then cleans the ZIP files by removing common unwanted files"
    echo "(e.g., .txt, .lnk, Thumbs.db, __MACOSX, .DS_Store)."
    echo "Requires 'parallel', 'arepack', and 'zip' commands."
    exit 0
fi

autoload zmv

if [ ! -x "`which parallel`" ]; then
	echo "Please install parallel first."
	exit -1
fi

touch xxxxxx.rar
find . -name "*.rar" | parallel --unsafe --bar -j4 'arepack {} {.}.zip && rm {}'
rm xxxxxx.rar

for i in **/*.zip; do
	zip --delete "$i" "*.txt"
	zip --delete "$i" "*.lnk"
	zip --delete "$i" "*.url"
	zip --delete "$i" "*.Url"
	zip --delete "$i" "*.URL"
	zip --delete "$i" "Thumbs*.db"
	zip --delete "$i" "__MACOSX*"
	zip --delete "$i" ".DS_Store"
	zip --delete "$i" "_____padding_file_"
	zip --delete "$i" "_____padding_file_*____"
	zip --delete "$i" ".@__thumb/*" ".@__thumb/"
done

echo "finish!"
