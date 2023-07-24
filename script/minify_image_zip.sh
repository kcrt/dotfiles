#!/usr/bin/env zsh

if [ ! -f "$1" ]; then
	echo "$1 does not exist!"
	exit
fi
rm -r /tmp/repack || echo "Start..."

fullname="$1"
filename="${fullname:t}"
stem="${filename:r}"
filesize=`wc -c $fullname | awk '{print $1}'`
(( org_filesize = filesize / 1024 / 1024))

print $stem

mkdir /tmp/repack/
mkdir /tmp/repack/REPACK_JPEG_HALF
unzip "$fullname" -d /tmp/repack/REPACK_JPEG_HALF

setopt GLOBSTARSHORT
echo "Shrinking..."
#for i in $(find /tmp/repack -name "*.jpg"); do
#	echo "$i"
#	mogrify -resize 50% "$i"
#done

~/dotfiles/script/minify_image_dir.sh /tmp/repack

echo "Repacking..."
mv "$fullname" "${fullname}.org"
zip -j -r "$fullname" /tmp/repack/REPACK_JPEG_HALF
rm -r /tmp/repack

filesize=`wc -c $fullname | awk '{print $1}'`
(( new_filesize = filesize / 1024 / 1024))

echo "done!"
echo "$org_filesize -->  $new_filesize  (MB)"
