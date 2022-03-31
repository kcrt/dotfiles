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
mkdir /tmp/repack/REPACK_AVIF
unzip "$fullname" -d /tmp/repack/REPACK_AVIF

setopt GLOBSTARSHORT
echo "Converting... (avif->jpg)"
find /tmp/repack -name "*.avif" | while read i
do
	echo "$i"
	convert "$i" -quality 90 "${i:r}.jpg"
	rm "$i"
done

echo "Repacking..."
mv "$fullname" "${fullname}.org"
zip -j -r "$fullname" /tmp/repack/REPACK_AVIF
rm -r /tmp/repack

filesize=`wc -c $fullname | awk '{print $1}'`
(( new_filesize = filesize / 1024 / 1024))

echo "done!"
echo "$org_filesize -->  $new_filesize  (MB)"
