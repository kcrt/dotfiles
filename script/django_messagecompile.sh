#!/bin/sh

if [ ! -e manage.py ]; then
	echo "manage.py not found : is here a right place?"
	exit
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
