#!/bin/bash

for outcode in j s e w8B w8L w16B w16L w32B w32L; do
	for incode in J S E W8B W8L W16B W16L W32B W32L; do
		echo "$incode -> $outcode:"
		echo "$1" | nkf -$incode -$outcode
	done
done


