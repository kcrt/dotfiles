#!/bin/sh

if [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ "$#" != 3 ]; then
    echo "Usage: $(basename "$0") <channelId> <writeKey> <data(dict)>"
    echo "Sends data to ambidata.io."
    echo "Example for data(dict): '{\"d1\": 1.1, \"d2\": 2.2}'"
    exit 0
fi

CHANNEL_ID=$1
WRITE_KEY=$2
DATA_DICT=$3
URL="http://ambidata.io/api/v2/channels/${CHANNEL_ID}/dataarray"

curl -X POST -H "Content-Type: application/json" -d "{\"writeKey\": \"$WRITE_KEY\", \"data\": [$DATA_DICT]}" "$URL"

if [ $? != 0 ]; then
	echo "Error"
fi
