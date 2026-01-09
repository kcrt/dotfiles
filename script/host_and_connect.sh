#!/bin/bash

# Get hostname
HOSTNAME=$(hostname)

# Check if running via mosh (only on Linux where pstree works properly)
IS_MOSH=0
if command -v pstree >/dev/null 2>&1; then
    if pstree -s $$ 2>/dev/null | grep -q mosh-server; then
        IS_MOSH=1
    fi
fi

# Check if running via SSH
if [ -n "$SSH_CONNECTION" ]; then
    # Extract local and remote IPs from SSH_CONNECTION
    if [ $IS_MOSH -eq 1 ]; then
        CONNECTION=$(echo -n "$SSH_CONNECTION" | sed -e 's/\(.*\) .* \(.*\) .*/\1 => \2/g')
        echo -n "mosh: $HOSTNAME ($CONNECTION)"
    else
        CONNECTION=$(echo -n "$SSH_CONNECTION" | sed -e 's/\(.*\) .* \(.*\) .*/\1 -> \2/g')
        echo -n "$HOSTNAME ($CONNECTION)"
    fi
else
    # Local connection
    echo -n "$HOSTNAME"
fi
