#!/bin/sh

TSA="http://sha256timestamp.ws.symantec.com/sha256/timestamp"
#TSA="http://timestamp.digicert.com"
#TSA="http://timestamp.apple.com/ts01"

if [ $# == 1 ]; then
	FILENAME=$1
	TSRFILE="$1.tsr"
elif [ $# == 2 ]; then
	FILENAME=$1
	TSRFILE=$2
else
	echo "$0 filename [certfile]"
	echo "Create timestamp"
	exit
fi

openssl ts -query -data "$FILENAME" -sha256 -cert | curl -o "$TSRFILE" -sSH 'Content-Type: application/timestamp-query' --data-binary @- "$TSA"
openssl ts -reply -in "$TSRFILE" -text
echo "---"
openssl ts -verify -in "$TSRFILE" -data "$FILENAME" -CApath /private/etc/ssl/certs/ # AppleTimestampCA.cer
