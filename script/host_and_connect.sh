#!/bin/bash

# Function to abbreviate IPv6 addresses (first 1 + last 2 segments)
abbreviate_ipv6() {
    local ip="$1"
    # Check if it's an IPv6 address (contains colons)
    if [[ "$ip" == *:* ]]; then
        # Extract first segment and last 2 segments
        local first=$(echo "$ip" | cut -d: -f1)
        local last2=$(echo "$ip" | rev | cut -d: -f1-2 | rev)
        echo "${first}:...:${last2}"
    else
        # IPv4 or other format - return as-is
        echo "$ip"
    fi
}

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
    CLIENT_IP=$(echo "$SSH_CONNECTION" | awk '{print $1}')
    SERVER_IP=$(echo "$SSH_CONNECTION" | awk '{print $3}')

    # Abbreviate IPs
    CLIENT_IP=$(abbreviate_ipv6 "$CLIENT_IP")
    SERVER_IP=$(abbreviate_ipv6 "$SERVER_IP")

    if [ $IS_MOSH -eq 1 ]; then
        echo -n "mosh: $HOSTNAME ($CLIENT_IP => $SERVER_IP)"
    else
        echo -n "$HOSTNAME ($CLIENT_IP -> $SERVER_IP)"
    fi
else
    # Local connection
    echo -n "$HOSTNAME"
fi
