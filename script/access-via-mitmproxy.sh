#!/usr/bin/env bash

mitmweb --set hardump=access_dump.har --set save_stream_file="access_dump" &
sleep 2
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --proxy-server="localhost:8080" --ignore-certificate-errors