#!/bin/sh
NUMMAIL=$(mail -H 2>&1 | grep "^.[UN]" | wc -l)

if [ $NUMMAIL = 0 ]; then
	echo ""
else
	echo " 📧"
fi
