#!/bin/sh

#===============================================================================
#
#          FILE:  get_router_macaddr.sh
#
#         USAGE:  ./get_router_macaddr.sh
#
#   DESCRIPTION:  Prints the MAC address of the default router.
#
#  REQUIREMENTS:  arp, netstat, awk, grep, head, ping
#          BUGS:  ---
#         NOTES:  ---
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

# Get the default gateway IP address (first default route if multiple exist)
DEFAULT_ROUTE=$(netstat -rn | grep '^default' | awk '{print $2}' | head -n 1)

if [ -z "$DEFAULT_ROUTE" ]; then
    echo "Error: Could not determine default gateway IP address." >&2
    echo "-"
    exit 1
fi

# Get the MAC address for the gateway IP
# 'arp -n "$DEFAULT_ROUTE"' queries the ARP cache for the gateway's MAC address.
# The '-n' option prevents DNS resolution, speeding up the query.
# 'awk '{print $4}'' extracts the MAC address from the output.
# Example arp output: ? (192.168.1.1) at 12:34:56:78:9a:bc on en0 ifscope [ethernet]
ROUTER_MAC=$(arp -n "$DEFAULT_ROUTE" | awk '{print $4}' | head -n 1)

# Validate the MAC address
if [ -z "$ROUTER_MAC" ] || [ "$ROUTER_MAC" = "(incomplete)" ]; then
    echo "Error: Could not determine MAC address for gateway $DEFAULT_ROUTE." >&2
    echo "-"
    exit 1
fi

# Print the MAC address
echo "$ROUTER_MAC"
