#!/usr/bin/env zsh

if [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ $# -eq 0 ]; then
    echo "Usage: echo \"Input text\" | $(basename "$0") <target_language_code>"
    echo "Translates text piped from stdin to the specified target language using the DeepL API."
    echo "DEEPL_API_KEY is taken from with-secret (asks for Touch ID unless allowed)."
    echo ""
    echo "Target language codes (examples):"
    echo "  EN - English"
    echo "  JA - Japanese"
    echo "  DE - German"
    echo "  FR - French"
    echo "  ES - Spanish"
    echo "  (See DeepL API documentation for a full list of supported languages)"
    exit 0
fi

# Secrets come from with-secret: re-run this script through it (Touch ID) if unset.
[ -n "${DEEPL_API_KEY:-}" ] || exec with-secret DEEPL_API_KEY -- "$0" "$@"

LANG=${(U)1}
if [[ "$LANG" == "jp" ]]; then
	LANG="ja"
fi

TRANS_LINE=""
TRANS_LINES=""
while read TRANS_LINE; do
	TRANS_LINES="$TRANS_LINES $TRANS_LINE"
done

curl -s https://api-free.deepl.com/v2/translate \
	-X POST \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-H "Authorization: DeepL-Auth-Key ${DEEPL_API_KEY}" \
	-d "text=${TRANS_LINES}"  \
	-d "target_lang=${LANG}" | jq -r ".translations[].text"
