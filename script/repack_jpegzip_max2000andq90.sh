#!/usr/bin/env zsh

if [ ! -f "$1" ]; then
	echo "$1 does not exist!"
	exit
fi
rm -r /tmp/repack || echo "Start..."

fullname="$1"
filename="${fullname:t}"
stem="${filename:r}"
filesize=$(wc -c $fullname | awk '{print $1}')
(( org_filesize = filesize / 1024 / 1024))

print $stem

mkdir /tmp/repack/
mkdir /tmp/repack/REPACK_JPEG_HALF
unzip "$fullname" -d /tmp/repack/REPACK_JPEG_HALF

setopt GLOBSTARSHORT

echo "Converting... (png->jpg)"
while IFS= read -r -d '' i; do
	echo "$i"
	magick "$i" -quality 100 "${i:r}_png.jpg"
	rm "$i"
done < <(find /tmp/repack -name "*.png" -print0)

echo "Resize and setting quality 90..."
find /tmp/repack/REPACK_JPEG_HALF -name "*.jpg" | parallel --progress -j 4 'magick mogrify -resize "2000x2000>" -quality 90 {}'

echo "Repacking..."
mv "$fullname" "${fullname}.org"
zip -j -r "$fullname" /tmp/repack/REPACK_JPEG_HALF
rm -r /tmp/repack

filesize=`wc -c $fullname | awk '{print $1}'`
(( new_filesize = filesize / 1024 / 1024))

echo "done!"
echo "$org_filesize -->  $new_filesize  (MB)"
