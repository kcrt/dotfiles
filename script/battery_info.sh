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
	BATRAW=$(ioreg -c AppleSmartBattery -r)
	# Read the value after `"Key" = ` instead of a fixed field number: ioreg indents
	# the properties with the registry tree (`|   "MaxCapacity" = 100`), and how many
	# of those prefix columns there are depends on how deep the node sits, which moved
	# by one on macOS 27 and shifted every $3 onto the `=` sign (division by zero).
	# The space around `=` also keeps this from matching the packed copies inside the
	# "BatteryData" dictionary (`"MaxCapacity"=100`).
	battery_prop() {
		printf '%s\n' "$BATRAW" | awk -v key="\"$1\" = " '
			(pos = index($0, key)) {
				value = substr($0, pos + length(key))
				sub(/[[:space:]]+$/, "", value)
				print value
				exit
			}'
	}
	MAXCAP=$(battery_prop MaxCapacity)
	CURCAP=$(battery_prop CurrentCapacity)
	BATTERY=$(battery_prop BatteryInstalled)
	FULL=$(battery_prop FullyCharged)
	AC=$(battery_prop ExternalConnected)
	BATPER=$(awk -v cur="$CURCAP" -v max="$MAXCAP" \
		'BEGIN { if (max + 0 > 0) printf("%.0f", cur / max * 100) }')
	if [ "$BATTERY" = "No" ] || [ -z "$BATPER" ]; then
		# Desktop PC, no battery (or the charge could not be read at all)
		echo "[🔌]"
	elif [ "$FULL" = "Yes" ] && [ "$AC" = "Yes" ]; then
		# Fully charged and using AC
		echo "[🔌]"
	elif [ "$AC" = "Yes" ]; then
		# Connected to AC, but not fully charged (charging)
		echo "${BATPER}% [🔌⚡️]"
	elif [ "$BATPER" -ge 30 ]; then
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
