#!/bin/sh

# beep when ping failed

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Continuously pings www.kcrt.net every 10 seconds."
    echo "If a ping fails, it attempts to produce a beep sound (\\a)."
    exit 0
fi

while [ 1 ]; do
	ping -c1 www.kcrt.net || echo "\a"
	sleep 10
done
