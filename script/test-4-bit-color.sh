#!/usr/bin/env zsh

# 30-37 and 90-97 are foreground colors
# 40-47 and 100-107 are background colors

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Displays a range of 4-bit background colors in the terminal."
    exit 0
fi

echo "\e[40m 0 \e[41m 1 \e[42m 2 \e[43m 3 \e[44m 4 \e[45m 5 \e[46m 6 \e[47m 7 "
echo "\e[100m*0*\e[101m*1*\e[102m*2*\e[103m*3*\e[104m*4*\e[105m*5*\e[106m*6*\e[107m*7*\e[0m"
