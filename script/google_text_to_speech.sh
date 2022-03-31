#!/bin/bash


# see: https://cloud.google.com/text-to-speech/docs/reference/rest/v1/text/synthesize?hl=ja
JSON="{
	'audioConfig': {
		'audioEncoding': 'MP3',
	},
	'input': {
		'text': '$1'
	},
	'voice': {
		'languageCode': 'en-US',
		'name': 'en-US-Wavenet-F'
	}
}"

echo $JSON > /tmp/voice.json

curl -X POST \
	-H "Authorization: Bearer "$(gcloud auth application-default print-access-token) \
	-H "Content-Type: application/json; charset=utf-8" \
	-d @/tmp/voice.json \
	-o /tmp/voice.output \
	"https://texttospeech.googleapis.com/v1/text:synthesize"

cat /tmp/voice.output | jq -r .audioContent | base64 -d > voice.mp3
echo "Saved as voice.mp3"
