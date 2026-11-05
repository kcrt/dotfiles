#!/bin/sh

if [ ! -d "$1" ]; then
	echo "cannot read!"
	echo "$0 sparsebundle"
	exit
fi

echo "convert $1 to large bund sparse bundle"
# sparse-band-size の単位は 512 バイトのセクタ: 262144 * 512 = 128MB
# UDSB = sparsebundle
before=`find "$1" -print | wc -l`
hdiutil convert "$1" -format UDSB -tgtimagekey sparse-band-size=262144 -o kcrt_largebund.sparsebundle
if [ $? -eq 0 ]; then
	mv "$1" "$1.old"
	mv "kcrt_largebund.sparsebundle" "$1"
	after=`find "$1" -print | wc -l`
	echo "number of files: $before -> $after"
	echo "finished! Old image is kept as $1.old"
	echo "After checking the new image, remove it with: rm -R \"$1.old\""
else
	echo "FAILED!"
fi

