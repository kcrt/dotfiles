#!/bin/sh

while getopts "abc:" c; do
	case $c in
		a)   echo "-a specified";;
		b)   echo "-b specified";;
		c)   echo "-c with $OPTARG";;
	esac
done
