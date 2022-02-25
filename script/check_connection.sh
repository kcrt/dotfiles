#!/bin/sh

# beep when ping failed

while [ 1 ]; do
	ping -c1 www.kcrt.net || echo "\a"
	sleep 10
done
