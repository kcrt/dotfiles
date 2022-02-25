#!/bin/zsh

#===============================================================================

for filename in **/.*; do
	if [[ "$filename" =~ .*\.AppleDouble.* ]]; then
		echo "Unknown $filename"
	elif [[ "$filename" =~ .*\.DS_Store ]]; then
		if [[ `file "$filename"` =~ .*(Apple\ Desktop\ Services\ Store|AppleDouble\ encoded\ Macintosh\ file) ]]; then
			echo "Deleting $filename ..."
			rm "$filename"
		else
			echo "Unknown $filename"
		fi
	elif [[ "$filename" =~ .*\/\._.* ]]; then
		if [[ `file "$filename"` =~ .*AppleDouble\ encoded\ Macintosh\ file ]]; then
			echo "Deleting $filename ..."
			rm "$filename"
		else
			echo "Unknown $filename"
		fi
	else
		echo "Skipping $filename"
	fi
done
