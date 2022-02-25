#!/bin/sh

#===============================================================================
#
#          FILE:  FILENAME_GOES_HERE.sh
#
#         USAGE:  ./battery.sh
#
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

if [ -x "`which ioreg`" ]; then
	BATSTR=`ioreg -c AppleSmartBattery -r | \
		awk '/MaxCapacity/{ MAX=$3 }
			 /CurrentCapacity/{ CURRENT=$3 }
			 /InstantTimeToEmpty/{ REMAIN=$3 }
			 /BatteryInstalled/{ BATTERY=$3 }
			 /FullyCharged/{ FULL=$3 }
			 /ExternalConnected/ {AC=$3}
			 END { printf("%5.1f%% %s %s %s\n", CURRENT/MAX*100, BATTERY, FULL, AC) }'`
	BATPER=`echo $BATSTR | cut -f1 -d" "`
	BATTERY=`echo $BATSTR | cut -f2 -d" "`
	FULL=`echo $BATSTR | cut -f3 -d" "`
	AC=`echo $BATSTR | cut -f4 -d" "`
	if [ "$BATTERY" = "No" ]; then
		echo "[🔌 ]"
	elif [ "$FULL" = "Yes" -a "$AC" = "Yes" ]; then
		echo "[🔌 ]"
	elif [ "$AC" = "Yes" ]; then
		echo "$BATPER [🔌 ⚡️]"
	else
		echo "$BATPER [🔋 ]"
	fi
fi
