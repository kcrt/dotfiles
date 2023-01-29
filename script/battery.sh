#!/bin/sh

#===============================================================================
#
#          FILE:  battery.sh
#         USAGE:  ./battery.sh
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#   DESCRIPTION:  Use for tmux status bar
#
#===============================================================================

if [ -x "`which ioreg`" ]; then
	# macOS
	BATSTR=`ioreg -c AppleSmartBattery -r | \
		awk '/"MaxCapacity"/{ MAX=$3 }
			 /"CurrentCapacity"/{ CURRENT=$3 }
			 /"InstantTimeToEmpty"/{ REMAIN=$3 }
			 /"BatteryInstalled"/{ BATTERY=$3 }
			 /"FullyCharged"/{ FULL=$3 }
			 /"ExternalConnected"/ {AC=$3}
			 END { printf("%5.1f %s %s %s\n", CURRENT/MAX*100, BATTERY, FULL, AC) }'`
	BATPER=`echo $BATSTR | cut -f1 -d" "`
	BATPER_INT=`echo $BATPER | cut -f1 -d"."`
	BATTERY=`echo $BATSTR | cut -f2 -d" "`
	FULL=`echo $BATSTR | cut -f3 -d" "`
	AC=`echo $BATSTR | cut -f4 -d" "`
	if [ "$BATTERY" = "No" ]; then
		# Desktop PC, no battery
		echo "[🔌]"
	elif [ "$FULL" = "Yes" -a "$AC" = "Yes" ]; then
		# Fully charged and using AC
		echo "[🔌]"
	elif [ "$AC" = "Yes" ]; then
		# Connected to AC, but not fully charged (charging)
		echo "${BATPER}% [🔌⚡️]"
	elif [ $BATPER_INT -ge 30 ]; then
		# Using battery
		echo "${BATPER}% [🔋]"
	else
		# Using battery, low battery
		echo "${BATPER}% [🪫]"
	fi
elif [ -d /sys/class/power_supply ]; then
	# Linux
	if [ -d /sys/class/power_supply/BAT* ]; then
		# There is a battery.
		BATPER=`cat /sys/class/power_supply/BAT*/capacity`
		STATUS=`cat /sys/class/power_supply/BAT*/status`
		if [ "$STATUS" = "Charging" ]; then
			echo "${BATPER}% [🔌⚡️]"
		elif [ "$STATUS" = "Full" ]; then
			echo "[🔌]"
		elif [ $BATPER -ge 30 ]; then
			echo "${BATPER}% [🔋]"
		else
			echo "${BATPER}% [🪫]"
		fi
	else
		# Desktop PC, no battery
		echo "[🔌]"
	fi
fi
