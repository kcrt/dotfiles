#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  deepl_document.sh
#
#         USAGE:  ./deepl_document.sh FILENAME [SOURCE_LANG TARGET_LANG]
#                 ./deepl_document.sh list_lang
#                 ./deepl_document.sh --help
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

show_help() {
    echo "Usage: $(basename "$0") FILENAME [SOURCE_LANG TARGET_LANG]"
    echo "       $(basename "$0") --list-lang"
    echo "       $(basename "$0") --help | -h"
    echo ""
    echo "Translates documents using the DeepL API."
    echo "Requires the DEEPL_API_KEY environment variable to be set."
    echo "Set DEBUG=1 for verbose information."
    echo ""
    echo "Arguments:"
    echo "  FILENAME        Path to the document to translate."
    echo "  SOURCE_LANG     Source language code (e.g., EN, JA). Default: EN."
    echo "  TARGET_LANG     Target language code (e.g., JA, DE). Default: JA."
    echo ""
    echo "Special Commands:"
    echo "  --list-lang     Display a link to DeepL's supported languages page."
    echo "  --help, -h      Show this help message."
    echo ""
    echo "Example: $(basename "$0") document.docx EN JA"
    exit 0
}

# Initialize variables
FILENAME=""
SOURCE_LANG="EN"
TARGET_LANG="JA"

# Parse arguments
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
fi

if [[ "$1" == "--list-lang" ]]; then
    echo "For a list of supported languages, please visit:"
    echo "https://developers.deepl.com/docs/getting-started/supported-languages"
    exit 0
fi

if [ $# -eq 0 ]; then
    echo "Error: No filename specified." >&2
    show_help # Call show_help which also exits
elif [ $# -eq 1 ]; then
    FILENAME=$1
    # SOURCE_LANG and TARGET_LANG keep their default values
elif [ $# -eq 2 ]; then
    echo "Error: Incorrect number of arguments." >&2
    echo "If specifying languages, provide both source and target." >&2
    show_help
elif [ $# -eq 3 ]; then
    FILENAME=$1
    SOURCE_LANG=${2:u} # Convert to uppercase
    TARGET_LANG=${3:u} # Convert to uppercase
else # More than 3 arguments
    echo "Error: Too many arguments." >&2
    show_help
fi

# check for $DEEPL_API_KEY
if [ -z "$DEEPL_API_KEY" ]; then
    echo "Error: DEEPL_API_KEY is not set." >&2
    exit 1
fi

# Check if FILENAME is set (it might not be if only 'list_lang' or '--help' was called and logic was different)
if [ -z "$FILENAME" ]; then
    echo "Error: Filename is missing." >&2
    show_help # This will exit
fi

if [ ! -f "$FILENAME" ]; then
    echo "Error: File '$FILENAME' not found." >&2
    exit 1
fi


echo "Sending '$FILENAME' to DeepL API for translation from $SOURCE_LANG to $TARGET_LANG..."

ret=$(curl -s -X POST 'https://api-free.deepl.com/v2/document' \
	-H "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
	-F "source_lang=$SOURCE_LANG" \
	-F "target_lang=$TARGET_LANG" \
	-F "file=@$FILENAME")

# store error code
send_document_code=$?

# show ret in DEBUG mode
if [ -n "$DEBUG" ]; then
    echo "Initial API response: $ret"
fi

# show error code from curl
if [ $send_document_code -ne 0 ]; then
    echo "Error: curl command for document upload failed with error code $send_document_code" >&2
    # Attempt to parse error from DeepL if possible, otherwise show curl's output if any
    if [[ -n "$ret" ]]; then
        error_message_json=$(echo "$ret" | jq -r '.message // .detail // ""' 2>/dev/null)
        if [[ -n "$error_message_json" && "$error_message_json" != "null" ]]; then
             echo "DeepL API Error: $error_message_json" >&2
        else
             echo "Raw response: $ret" >&2
        fi
    fi
    exit 1
fi

document_id=$(echo "$ret" | jq -r '.document_id')
document_key=$(echo "$ret" | jq -r '.document_key')

if [[ "$document_id" == "null" || "$document_key" == "null" ]]; then
    echo "Error: Could not get document_id or document_key from DeepL API response." >&2
    echo "Response: $ret" >&2
    exit 1
fi

if [ -n "$DEBUG" ]; then
    echo "document_id: $document_id"
    echo "document_key: $document_key"
fi

echo "Waiting for translation to complete..."
while [ true ]; do
    sleep 5
    ret_status=$(curl --silent -m 30 -X POST "https://api-free.deepl.com/v2/document/$document_id" \
	    -H "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
	    -d "document_key=$document_key")
    
    if [ -n "$DEBUG" ]; then
        echo "Status check response: $ret_status"
    fi
    
    trans_status=$(echo "$ret_status" | jq -r '.status')
    
    if [ "$trans_status" = "done" ]; then
        billed_characters=$(echo "$ret_status" | jq -r '.billed_characters')
        echo "Done! Billed characters: $billed_characters"
        break
    elif [ "$trans_status" = "error" ]; then
        error_message=$(echo "$ret_status" | jq -r '.message // .error_message // "Unknown error"')
        echo "Error: Translation failed: $error_message" >&2
        exit 1
    elif [ "$trans_status" = "queued" ]; then
        echo "Translation is in queue."
    elif [ "$trans_status" = "translating" ]; then
        seconds_remaining=$(echo "$ret_status" | jq -r '.seconds_remaining // "N/A"')
        echo "$seconds_remaining seconds remaining ($trans_status)..."
    elif [[ "$trans_status" == "null" ]]; then
        echo "Error: Failed to get translation status. Response was: $ret_status" >&2
        exit 1
    else
        echo "Unknown status: $trans_status. Response: $ret_status"
    fi
done

output_filename="${FILENAME:r}_${TARGET_LANG}.${FILENAME:e}"
echo "Downloading translated document to '$output_filename'..."

curl -s -X POST "https://api-free.deepl.com/v2/document/$document_id/result" \
	-H "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
	-d "document_key=$document_key" \
	--output "$output_filename"

if [ $? -eq 0 ]; then
    echo "Translated document saved as '$output_filename'."
else
    echo "Error: Failed to download translated document." >&2
    exit 1
fi
