#!/bin/sh


# zip each folder in the current directory parallelly
# usage: zipeachfolder.sh

find . -maxdepth 1 -type d -print | grep -v "^.$" | parallel --progress --bar zip -q -r {}.zip {}
