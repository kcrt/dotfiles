#!/bin/sh

#===============================================================================
#
#          FILE:  check_banbix.sh
#
#         USAGE:  ./check_banbix.sh
#
#   DESCRIPTION:  Check if a product is in stock on banbix.com
#
#  REQUIREMENTS:  curl
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Checks if a specific product ('ソフトシングル格外品100個') is in stock on banbix.com."
    echo "Exits with 0 if out of stock or if the page loads correctly."
    echo "Prints a message and exits with non-zero if an error occurs or if the product is in stock."
    exit 0
fi

# URL of the product page to check
URL="https://banbix.com/products/detail/141"

# Fetch the webpage and check for stock status
response=$(curl -s "$URL")

if ! echo "$response" | grep -q "ソフトシングル格外品100個"; then
    echo "check banbix error"
    exit 1
fi

if echo "$response" | grep -i -q "error\|エラー"; then
    echo "check banbix error"
    exit 1
fi

if echo "$response" | grep -q '<span class="emptyInfo">在庫なし</span>'; then
    exit 0
else
    echo "入荷があります: ${URL}"
fi
