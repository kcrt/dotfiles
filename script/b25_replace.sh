#!/bin/sh

if [ $# -ne 1 ]; then
	echo "$0 b25file"
	exit
fi

echo "Un'b25'ing $1..."

pv "$1" > /tmp/b25_converting.ts
mv "$1" "$1.backup"
b25 /tmp/b25_converting.ts "$1"
if [ $? = 0 -a -f "$1"]; then
	rm "$1.backup"
else
	echo "!!!ERROR!!!"
	mv "$1.backup" "$1"
fi
