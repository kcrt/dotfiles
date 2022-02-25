#!/bin/sh

if [ ! -d "$1" ]; then
	echo "$1 is not directory!"
	exit
fi

nfiles=`find "$1" -print|wc -l`
echo "There are $nfiles files in this cage."
echo "Start compressing $1..."
zip -r "$1.zip" "$1"
if [ $? -eq 0 ]; then
	echo "Deleting $1..."
	rm -R -v "$1"
	echo "$nfiles were successfully archived to one zip file."
else
	echo "ERROR: Cannot create archive."
fi
