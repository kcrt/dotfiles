#!/bin/sh

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0") <b25file>"
    echo "Replaces the input b25file with its 'un-b25'ed' version."
    echo "A backup of the original file is made with a .backup extension during the process."
    exit 0
fi

if [ $# -ne 1 ]; then
	echo "Usage: $(basename "$0") <b25file>"
	echo "For more help, run: $(basename "$0") --help"
	exit 1
fi

echo "Un'b25'ing $1..."

pv "$1" > /tmp/b25_converting.ts
mv "$1" "$1.backup"
b25 /tmp/b25_converting.ts "$1"
if [ $? -eq 0 -a -f "$1" ]; then
	rm "$1.backup"
else
	echo "!!!ERROR!!!"
	mv "$1.backup" "$1"
fi
