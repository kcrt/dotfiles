#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  deepl_document.sh
#
#         USAGE:  ./deepl_document.sh FILENAME [SOURCE_LANG TARGET_LANG]
#                 ./deepl_document.sh list_lang
#
#   DESCRIPTION:  Translate documents via DeepL API
#
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#          NOTE:  Before running this script, set DEEPL_API_KEY in your environment.
#                 Set DEBUG=1 for verbose information
#
#===============================================================================



if [ "$1" = "list_lang" ]; then
    echo "https://developers.deepl.com/docs/getting-started/supported-languages"
    exit 0
fi

if [ $# -eq 1 ]; then
    FILENAME=$1
    SOURCE_LANG="EN"
    TARGET_LANG="JA"
elif [ $# -eq 3 ]; then
    FILENAME=$1
    SOURCE_LANG=$2
    TARGET_LANG=$3
else
    echo "Usage: $0 FILENAME [SOURCE_LANG TARGET_LANG]"
    echo "e.g. $0 document.docx EN JA"
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

# store error code
send_document_code=$?

# show ret in DEBUG mode
if [ -n "$DEBUG" ]; then
    echo $ret
fi

# show error code
if [ $send_document_code -ne 0 ]; then
    echo "Error: curl command failed with error code $send_document_code"
    exit 1
fi

document_id=`echo $ret | jq -r '.document_id'`
document_key=`echo $ret | jq -r '.document_key'`

if [ -n "$DEBUG" ]; then
    echo "document_id: $document_id"
    echo "document_key: $document_key"
fi

echo "Waiting for translation to complete..."
while [ true ]; do
    sleep 5
    ret=`curl --silent -m 30 -X POST "https://api-free.deepl.com/v2/document/$document_id" \
	-H "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
	-d "document_key=$document_key"`
    if [ -n "$DEBUG" ]; then
        echo $ret
    fi
    trans_status=`echo $ret | jq -r '.status'`
    if [ "$trans_status" = "done" ]; then
        billed_characters=`echo $ret | jq -r '.billed_characters'`
        echo "Done! Billed characters: $billed_characters"
        break
    elif [ "$trans_status" = "error" ]; then
        error_message=`echo $ret | jq -r '.error_message'`
        echo "Error: Translation failed: $error_message"
        exit 1
    elif [ "$trans_status" = "queued" ]; then
        echo "Translation is in queue."
    elif [ "$trans_status" = "translating" ]; then
        seconds_remaining=`echo $ret | jq -r '.seconds_remaining'`
        echo "$seconds_remaining [sec] ($trans_status)..."
    else
        echo "Unknown status: $trans_status"
    fi
done

curl -X POST "https://api-free.deepl.com/v2/document/$document_id/result" \
	-H "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
	-d "document_key=$document_key" \
	--output "${FILENAME:r}_${TARGET_LANG}.${FILENAME:e}"
