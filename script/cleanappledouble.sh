#!/bin/zsh

#===============================================================================

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Recursively finds and deletes .DS_Store files and AppleDouble files (._*)"
    echo "in the current directory and its subdirectories."
    echo "It checks the file type before deleting to avoid removing legitimate dotfiles."
    exit 0
fi

for filename in **/.*; do
	if [[ "$filename" =~ .*\.AppleDouble.* ]]; then
		echo "Unknown $filename"
	elif [[ "$filename" =~ .*\.DS_Store ]]; then
		if [[ `file "$filename"` =~ .*(Apple\ Desktop\ Services\ Store|AppleDouble\ encoded\ Macintosh\ file) ]]; then
			echo "Deleting $filename ..."
			rm "$filename"
		elif [[ ! -s "$filename" ]]; then
			echo "Deleting empty $filename ..."
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
