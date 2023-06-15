#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  deepl_document.sh
#
#         USAGE:  ./deepl_document.sh FILENAME [SOURCE_LANG TARGET_LANG]
#
#   DESCRIPTION:  Translate documents via DeepL API
#
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

if [ $# -eq 1 ]; then
    FILENAME=$1
    SOURCE_LANG="JA"
    TARGET_LANG="EN-US"
elif [ $# -eq 3 ]; then
    FILENAME=$1
    SOURCE_LANG=$2
    TARGET_LANG=$3
else
    echo "Usage: $0 FILENAME [SOURCE_LANG TARGET_LANG]"
    exit 1
fi

# check for $DEEPL_API_KEY
if [ -z "$DEEPL_API_KEY" ]; then
    echo "Error: DEEPL_API_KEY is not set."
    exit 1
fi

echo "Sending $FILENAME to DeepL API for translation from $SOURCE_LANG to $TARGET_LANG..."

ret=`curl -X POST 'https://api-free.deepl.com/v2/document' \
	-H "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
	-F "source_lang=$SOURCE_LANG" \
	-F "target_lang=$TARGET_LANG" \
	-F "file=@$FILENAME"`

document_id=`echo $ret | jq -r '.document_id'`
document_key=`echo $ret | jq -r '.document_key'`

echo "Waiting for translation to complete..."
while [ true ]; do
    sleep 5
    ret=`curl -X POST "https://api-free.deepl.com/v2/document/$document_id" \
	-H "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
	-d "document_key=$document_key"`
    status=`echo $ret | jq -r '.status'`
    seconds_remaining=`echo $ret | jq -r '.seconds_remaining'`
    if [ "$status" = "done" ]; then
        break
    else
        echo "$seconds_remaining [sec]..."
    fi
done
echo "Done!"

curl -X POST "https://api-free.deepl.com/v2/document/$document_id/result" \
	-H "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
	-d "document_key=$document_key" \
	--output "${FILENAME:r}_${TARGET_LANG}.${FILENAME:e}"
