#!/usr/bin/env zsh


if [[ "$1" == "" ]]; then
	echo "Usage: echo \"Hello world\" | $0 en|ja"
	exit
fi

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
	-d auth_key=${DEEPL_API_KEY} \
	-d "text=${TRANS_LINES}"  \
	-d "target_lang=${LANG}" | jq -r ".translations[].text"
