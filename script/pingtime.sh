#!/usr/bin/env bash

pingret=`ping -c 3 -q kcrt.net`
line=`echo $pingret | grep "avg" | cut -f2 -d"=" | sed -e 's/ ms//'`
avg=`echo $line | cut -f1 -d"/"`
sd=`echo $line | cut -f4 -d"/"`

if [[ "$1" == "--avg" ]]; then
	printf "%.3f" $avg
	exit
fi

if [[ `echo $pingret | grep "3 packets received"` ]]; then
	# 3 packets received
	if [[ `echo "$avg < 1" | bc` == 1 ]]; then
		printf "%.3f±%.3fms" $avg $sd
	elif [[ `echo "$avg < 10" | bc` == 1 ]]; then
		printf "%.1f±%.1fms" $avg $sd
	else
		printf "%.0f±%.0fms" $avg $sd
	fi
elif [[ `echo $pingret | grep "0 packets received"` ]]; then
	echo "[x]"
else
	printf "%.0f±%.0fms [!]" $avg $sd
fi
