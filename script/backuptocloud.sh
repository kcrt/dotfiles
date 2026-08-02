#!/usr/bin/env zsh

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0") <file_or_directory_to_backup>"
    echo "Backs up the specified file or directory to Google Cloud Storage."
    echo "The backup will be placed in gs://auto.backup.kcrt.net/manual/YYYY/MM/"
    exit 0
fi

if [ -z "$1" ]; then
    echo "Usage: $(basename "$0") <file_or_directory_to_backup>"
    echo "For more help, run: $(basename "$0") --help"
    exit 1
fi

YEAR=$(date +%Y)
MONTH=$(date +%m)

echo "sending $1 to cloud☁️ .."
# gcloud storage parallelizes by default, so gsutil's -m has no counterpart.
if [[ -d "$1" ]]; then
	gcloud storage cp -r "$1" gs://auto.backup.kcrt.net/manual/$YEAR/$MONTH/
else
	gcloud storage cp "$1" gs://auto.backup.kcrt.net/manual/$YEAR/$MONTH/
fi
