#!/bin/sh

# Secrets come from with-secret: re-run this script through it (Touch ID) if unset.
[ -n "${OPENAI_API_KEY:-}" ] || exec with-secret OPENAI_API_KEY -- "$0" "$@"

# infinit loop
while true; do
    # ask for file name
    echo "Please enter the path to the audio file you want to transcribe:"
    read -r filename
    # check if file exists
    if [ -f "$filename" ]; then
        break
    else
        echo "File does not exist. Please try again."
    fi
done

outputfile="${filename%.*}.txt"

curl --request POST \
  --url https://api.openai.com/v1/audio/transcriptions \
  --header "Authorization: Bearer $OPENAI_API_KEY" \
  --header 'Content-Type: multipart/form-data' \
  --form file=@"$filename" \
  --form model=whisper-1 \
  --form language=$lang \
  --form response_format=text | tee "$outputfile"
