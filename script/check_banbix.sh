#!/bin/sh

#===============================================================================
#
#          FILE:  check_banbix.sh
#
#         USAGE:  ./check_banbix.sh
#
#   DESCRIPTION:  Check if a product is in stock on banbix.com
#
#       OPTIONS:  ---
#  REQUIREMENTS:  curl
#          BUGS:  ---
#         NOTES:  ---
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#      REVISION:  $Id$
#
#===============================================================================

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
    echo "入荷があります :${URL}"
fi
