#!/bin/sh

if [ ! -d "$1" ]; then
	echo "cannot read!"
	exit
fi

echo "convert $1 to large bund sparse bundle (10gb)"
hdiutil create -size 10g -format UDSB -volname "$1" -srcfolder "$1" -tgtimagekey sparse-band-size=131072 -o "$1.sparsebundle" -encryption -stdinpass
if [ $? -eq 0 ]; then
	echo "finished! Now removing old file..."
	rm -R "$1"
else
	echo "FAILED!"
fi

