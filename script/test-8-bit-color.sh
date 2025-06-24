#!/bin/bash

# Original is: https://tools.paco.bg/14/

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Displays a range of 8-bit foreground and background colors in the terminal."
    exit 0
fi

for fgbg in 38 48 ; do # Foreground / Background
    for color in {0..255} ; do # Colors
        # Display the color
        printf "\e[${fgbg};5;%sm %3s \e[0m" "$color" "$color"
        # Display 18 colors per lines
        if [ $(((color + 1) % 18)) == 4 ] ; then
            echo # New line
        fi
    done
    echo # New line
done
 
exit 0
