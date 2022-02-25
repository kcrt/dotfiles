#!/bin/sh


for i in *; do
	if [[ -d $i ]]; then
		echo "===== $i ====="
		zip -r "$i".zip "$i"
	fi
done
