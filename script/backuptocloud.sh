#!/usr/bin/env zsh

echo "sending $1 to cloud☁️ .."
if [[ -d "$1" ]]; then
	gsutil -m cp -r "$1" gs://backup.kcrt.net/manual/
else
	gsutil -m cp "$1" gs://backup.kcrt.net/manual/
fi
