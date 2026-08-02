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

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Displays battery status information, suitable for use in status bars (e.g., tmux)."
    echo "Output format varies based on battery state (charging, full, discharging, low)."
    exit 0
fi

if command -v ioreg > /dev/null 2>&1; then
	# macOS
	BATSTR=$(ioreg -c AppleSmartBattery -r | \
		awk '/"MaxCapacity"/{ MAX=$3 }
			 /"CurrentCapacity"/{ CURRENT=$3 }
			 /"InstantTimeToEmpty"/{ REMAIN=$3 }
			 /"BatteryInstalled"/{ BATTERY=$3 }
			 /"FullyCharged"/{ FULL=$3 }
			 /"ExternalConnected"/ {AC=$3}
			 END { printf("%.1f %s %s %s\n", CURRENT/MAX*100, BATTERY, FULL, AC) }')
	BATPER=$(echo "$BATSTR" | cut -f1 -d" ")
	BATPER_INT=$(echo "$BATPER" | cut -f1 -d".")
	BATTERY=$(echo "$BATSTR" | cut -f2 -d" ")
	FULL=$(echo "$BATSTR" | cut -f3 -d" ")
	AC=$(echo "$BATSTR" | cut -f4 -d" ")
	if [ "$BATTERY" = "No" ]; then
		# Desktop PC, no battery
		echo "[🔌]"
	elif [ "$FULL" = "Yes" ] && [ "$AC" = "Yes" ]; then
		# Fully charged and using AC
		echo "[🔌]"
	elif [ "$AC" = "Yes" ]; then
		# Connected to AC, but not fully charged (charging)
		echo "${BATPER}% [🔌⚡️]"
	elif [ "$BATPER_INT" -ge 30 ]; then
		# Using battery
		echo "${BATPER}% [🔋]"
	else
		# Using battery, low battery
		echo "${BATPER}% [🪫]"
	fi
elif [ -d /sys/class/power_supply ]; then
	# Linux
	BAT_PATH=$(find /sys/class/power_supply/ -name 'BAT*' | head -n 1)
	# Check if there is a battery
	if [ -n "$BAT_PATH" ] && [ -e "$BAT_PATH/capacity" ]; then
		BATPER=$(cat "$BAT_PATH/capacity")
		STATUS=$(cat "$BAT_PATH/status")
		if [ "$STATUS" = "Charging" ]; then
			echo "${BATPER}% [🔌⚡️]"
		elif [ "$STATUS" = "Full" ]; then
			echo "[🔌]"
		elif [ "$BATPER" -ge 30 ]; then
			echo "${BATPER}% [🔋]"
		else
			echo "${BATPER}% [🪫]"
		fi
	else
		# Desktop PC, no battery
		echo "[🔌]"
	fi
fi
