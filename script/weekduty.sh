#!/bin/sh

#===============================================================================
#
#          FILE:  weekduty.sh
#
#         USAGE:  ./weekduty.sh
#
#   DESCRIPTION:  Find this week's duty table and show with qlmanage
#
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

TARGET_DIR="$HOME/Desktop/duty"
if [ ! -d "$TARGET_DIR" ]; then
    echo "Directory $TARGET_DIR does not exist."
    exit 1
fi

# Find this week's duty table (PDF file begin with "★")
DUTY_FILE=$(find "$TARGET_DIR" -name "★*.pdf" -print -quit)
if [ -z "$DUTY_FILE" ]; then
    echo "No duty file found."
    exit 1
fi

# Show the duty table with qlmanage
qlmanage -p "$DUTY_FILE" &