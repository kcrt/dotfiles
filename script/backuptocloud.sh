#!/usr/bin/env zsh

YEAR=$(date +%Y)
MONTH=$(date +%m)

echo "sending $1 to cloud☁️ .."
if [[ -d "$1" ]]; then
	gsutil -m cp -r "$1" gs://backup.kcrt.net/manual/$YEAR/$MONTH/
else
	gsutil -m cp "$1" gs://backup.kcrt.net/manual/$YEAR/$MONTH/
fi
