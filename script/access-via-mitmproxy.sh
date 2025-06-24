#!/usr/bin/env bash

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Starts mitmweb and Google Chrome configured to proxy through mitmweb."
    echo "Saves HAR dump to 'access_dump.har' and stream to 'access_dump'."
    exit 0
fi

mitmweb --set hardump=access_dump.har --set save_stream_file="access_dump" &
sleep 2
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --proxy-server="localhost:8080" --ignore-certificate-errors
