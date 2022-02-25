#!/bin/zsh

autoload zmv

if [ ! -x "`which parallel`" ]; then
	echo "Please install parallel first."
	exit -1
fi

touch xxxxxx.rar
find . -name "*.rar" | parallel --bar -j4 'arepack {} {.}.zip && rm {}'
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
done

echo "finish!"
