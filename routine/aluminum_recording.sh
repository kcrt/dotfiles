#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  aluminum_recording.sh
#         USAGE:  ./aluminum_recording.sh
#   DESCRIPTION:  This script is a backup utility for recorded files.
#  REQUIREMENTS:  rsync
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

# Check if rsync is installed
if ! command -v rsync &> /dev/null; then
    OSNotify "rsync is not installed. Please install it first."
    exit 1
fi

# Check if machine is aluminum
if [[ "$HOST" != "aluminum.local" ]]; then
    OSNotify "This script is intended to be run on aluminum.local only."
    exit 1
fi

# Check if qnap is reachable
if ! ping -c 1 qnap.local &> /dev/null; then
    OSNotify "QNAP is not reachable. Please check your network connection."
    exit 1
fi

# Start backup of recording files
if [[ -d /Volumes/Private/Recording/ ]]; then
    n=`ls $HOME/nosync/RecordingToSend/*.MP3 | wc -l`
    echo "There are $n mp3 file(s)."
    if [[ "$n" -ge 1 ]]; then
        zmv -v "$HOME/nosync/RecordingToSend/*_(*)_(*)A0.MP3" '/Volumes/Private/Recording/Recorder/$1_$2.MP3'
    fi
    n=`ls $HOME/nosync/RecordingToSend/*.m4a | wc -l`
    echo "There are $n m4a file(s)."
    if [[ "$n" -ge 1 ]]; then
        for m4afile in ~/nosync/RecordingToSend/*.m4a; do
            RECORDINGDATE=`ffprobe -loglevel quiet -of json -show_entries stream "$m4afile" | jq -r '.streams[0].tags.creation_time' | cut -c 1-19 | sed 's/:/-/g'`
            mv -v "$m4afile" "/Volumes/Private/Recording/VoiceMemo/${RECORDINGDATE}_${m4afile:t}"
        done
    fi
    echo "Starting transcription..."
    for i in /Volumes/Private/Recording/VoiceMemo/*.m4a; do
        if [ ! -e "${i:r}.txt" ]; then
            uv tool run parakeet-mlx --model mlx-community/parakeet-tdt_ctc-0.6b-ja "$i" --output-dir /Volumes/Private/Recording/VoiceMemo/
            # Use srt format and rename to txt after transcription
            mv "${i:r}.srt" "${i:r}.txt"
        fi
    done
    # zmv -W '/Volumes/Private/Recording/VoiceMemo/*.srt' '/Volumes/Private/Recording/VoiceMemo/*.txt'

    # Transcript one mp3 file at a time
    for i in /Volumes/Private/Recording/Recorder/*.MP3; do
        if [ ! -e "${i:r}.txt" ]; then
            uv tool run parakeet-mlx --model mlx-community/parakeet-tdt_ctc-0.6b-ja "$i" --output-dir /Volumes/Private/Recording/Recorder/
            mv "${i:r}.srt" "${i:r}.txt"
            # exit for
            break
        fi
    done

fi