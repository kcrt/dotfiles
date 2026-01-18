#!/usr/bin/env bash

# translate.sh - Translate text using ollama translategemma:12b model
# Usage: translate.sh SOURCE_CODE TARGET_CODE [TEXT]
# Example: translate.sh en ja "Hello, world!"
# Example: echo "Hello" | translate.sh en ja

set -e

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 SOURCE_CODE TARGET_CODE [TEXT]" >&2
    echo "Example: $0 en ja \"Hello, world!\"" >&2
    echo "Example: echo \"Hello\" | $0 en ja" >&2
    exit 1
fi

SOURCE_CODE="$1"
TARGET_CODE="$2"

# Read text from 3rd argument or stdin
if [ $# -ge 3 ]; then
    TEXT="$3"
else
    TEXT=$(cat)
fi

# Check if text is provided
if [ -z "$TEXT" ]; then
    echo "Error: No input text provided" >&2
    exit 1
fi

# Get language names from codes
# See: https://ollama.com/library/translategemma
declare -A LANG_NAMES
LANG_NAMES[en]="English"
LANG_NAMES[ja]="Japanese"
LANG_NAMES[ja-JP]="Japanese"
LANG_NAMES[es]="Spanish"
LANG_NAMES[fr]="French"
LANG_NAMES[de]="German"
LANG_NAMES[it]="Italian"
LANG_NAMES[zh]="Chinese"
LANG_NAMES[zh-TW]="Chinese"
LANG_NAMES[zh-Hans]="Chinese"
LANG_NAMES[zh-Hant]="Chinese"
LANG_NAMES[ko]="Korean"

SOURCE_LANG="${LANG_NAMES[$SOURCE_CODE]:-$SOURCE_CODE}"
TARGET_LANG="${LANG_NAMES[$TARGET_CODE]:-$TARGET_CODE}"

# Build the prompt
PROMPT="You are a professional ${SOURCE_LANG} (${SOURCE_CODE}) to ${TARGET_LANG} (${TARGET_CODE}) translator. Your goal is to accurately convey the meaning and nuances of the original ${SOURCE_LANG} text while adhering to ${TARGET_LANG} grammar, vocabulary, and cultural sensitivities.
Produce only the ${TARGET_LANG} translation, without any additional explanations or commentary. Please translate the following ${SOURCE_LANG} text into ${TARGET_LANG}:


${TEXT}"

# Call ollama with the translategemma:12b model
ollama run translategemma:12b "$PROMPT"
