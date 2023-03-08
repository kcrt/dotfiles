#!/bin/sh

if [ "$OPENAI_API_KEY" = "" ]; then
    echo "Please set the OPENAI_API_KEY environment variable"
    exit 1
fi

# infinit loop
while true; do
    # ask for file name
    echo "Please enter the path to the audio file you want to transcribe:"
    read filename
    # check if file exists
    if [ -f "$filename" ]; then
        break
    else
        echo "File does not exist. Please try again."
    fi
done

curl --request POST \
  --url https://api.openai.com/v1/audio/transcriptions \
  --header "Authorization: Bearer $OPENAI_API_KEY" \
  --header 'Content-Type: multipart/form-data' \
  --form file=@"$filename" \
  --form model=whisper-1 \
  --form language=$lang \
  --form response_format=text | tee "$outputfile"

rm "$tmpfile"