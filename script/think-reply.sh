#!/bin/bash

#===============================================================================
#
#          FILE:  think-reply.sh
#
#         USAGE:  ./think-reply.sh
#
#   DESCRIPTION:  Think reply of e-mail message using ollama.
#
#===============================================================================

MESSAGE=$(pbpaste)
# Check language of message
if [[ $MESSAGE =~ [ぁ-んァ-ン] ]]; then
    LANGUAGE="ja"
    ORDER="下記のようなメールを受け取りました。これに対して適切な返信を教えてください。返信以外の内容は出力しなくてよいです。また、署名も不要です。\n ただし、相手の所属と名前 + 敬称を先頭に書いてください。 敬称は相手が医師の場合は先生、それ以外は様でお願いします。"
    MODEL="elyza:jp8b"
else
    LANGUAGE="en"
    ORDER="I received an e-mail like the following. Please let me know the appropriate reply. You don't need to output anything other than the reply message."
    MODEL="llama3.2:latest"
fi

if [ -e ~/my_profile_${LANGUAGE}.txt ]; then
    MY_PROFILE=$(cat ~/my_profile_${LANGUAGE}.txt)
else
    echo "Please create ~/my_profile_${LANGUAGE}.txt"
    echo "Example:"
    echo "My name is Kyohei Takahashi. I work at XXXX."
    exit
fi
LANGUAGE=""

PROMPT=$(cat <<EOF
$MY_PROFILE

$ORDER
******
$MESSAGE
EOF
)

echo "$PROMPT" | ollama run $MODEL | tee /tmp/mail_reply.txt
cat /tmp/mail_reply.txt | pbcopy
rm /tmp/mail_reply.txt
