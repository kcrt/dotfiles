#!/bin/sh

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Compiles Django message files (.po to .mo) for localization."
    echo "It iterates through subdirectories, creates 'locale' if it doesn't exist,"
    echo "runs 'makemessages' for Japanese (ja), and then 'compilemessages'."
    echo "This script should be run from the Django project's root directory (where manage.py is located)."
    exit 0
fi

if [ ! -e manage.py ]; then
	echo "manage.py not found : is here a right place?"
	echo "Run this script from your Django project's root directory."
	echo "For more help, run: $(basename "$0") --help"
	exit 1
fi


for i in *; do
    if [ -d $i ]; then
		echo "[$i]"
        cd $i
        if [ ! -d "locale" ]; then
            echo "locale not found, making..."
            mkdir locale
        fi
        ../manage.py makemessages -v1 --locale=ja -e html -e json -e py
        ../manage.py compilemessages
        cd ..
    fi
done
