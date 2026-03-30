#!/bin/bash

#===============================================================================
#
#          FILE:  think-reply-openai.sh
#         USAGE:  ./think-reply-openai.sh
#   DESCRIPTION:  Think reply of e-mail message using OpenAI API.
#
#===============================================================================

if [ "$OPENAI_API_KEY" = "" ]; then
    echo "Please set the OPENAI_API_KEY environment variable"
    exit 1
fi

MESSAGE=$(pbpaste)
# Check language of message
if [[ $MESSAGE =~ [ぁ-んァ-ン] ]]; then
    LANGUAGE="ja"
    ORDER="下記のようなメールを受け取りました。これに対して適切な返信を教えてください。相手の所属と名前 + 敬称を先頭に書いてください。敬称は相手が医師の場合は先生、それ以外は様でお願いします。返信以外の内容は出力しなくてよいです。また、署名も不要です。"
else
    LANGUAGE="en"
    ORDER="I received an e-mail like the following. Please let me know the appropriate reply. You don't need to output anything other than the reply message."
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

# replace PROMPT to JSON safe string, considering line breaks and double quotes
PROMPT=$(echo "$PROMPT" | sed -e 's/"/\\"/g' | sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/\\n/g')


ret=$(curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -s \
  -d "{
    \"model\": \"gpt-4o\",
    \"messages\": [
      {
        \"role\": \"system\",
        \"content\": \"You are a helpful assistant.\"
      },
      {
        \"role\": \"user\",
        \"content\": \"${PROMPT}\"
      }
    ]
  }")

echo $ret | jq -r '.choices[0].message.content'
echo $ret | jq -r '.choices[0].message.content' | pbcopy
 