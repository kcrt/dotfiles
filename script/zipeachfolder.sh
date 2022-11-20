#!/bin/sh


# zip each folder in the current directory parallelly
# usage: zipeachfolder.sh

find . -maxdepth 1 -type d -print0 | parallel --progress --bar -0 zip -q -r {}.zip {}
