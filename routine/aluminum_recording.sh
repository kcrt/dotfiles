#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  aluminum_recording.sh
#         USAGE:  ./aluminum_recording.sh
#   DESCRIPTION:  This script is a backup utility for recorded files.
#  REQUIREMENTS:  ffprobe, jq, uv
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh
# The recording directories live on an SMB share, where a plain zsh glob hands
# back names that cannot be opened again. See the file for the details.
source ${DOTFILES}/script/nfd_safe_glob.sh
autoload -Uz zmv

RECORDING_DIR=/Volumes/Private/Recording
VOICEMEMO_DIR="$RECORDING_DIR/VoiceMemo"
RECORDER_DIR="$RECORDING_DIR/Recorder"
INBOX_DIR=/nosync/RecordingToSend
PARAKEET_MODEL=mlx-community/parakeet-tdt_ctc-0.6b-ja
# One recorder MP3 is hours long, so transcribing the whole backlog would keep
# maintain.sh busy all night. Take the oldest one and leave the rest for the
# next run.
RECORDER_TRANSCRIPTS_PER_RUN=1

# ffprobe reads the recording date, jq pulls it out of ffprobe's JSON and uv
# runs the transcriber. Any of them missing used to turn into a pile of
# half-finished moves instead of a clear error.
for required_command in ffprobe jq uv; do
    if ! command -v "$required_command" &> /dev/null; then
        OSError "$required_command is not installed. Please install it first."
        exit 1
    fi
done

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

# A missing share used to skip everything below and still report success, which
# is the one outcome that must not happen quietly here.
if [[ ! -d "$RECORDING_DIR" ]]; then
    OSError "$RECORDING_DIR not found. Is /Volumes/Private mounted?"
    exit 1
fi

# $INBOX_DIR is local (APFS), where names survive a glob unchanged, so the two
# ingest functions below can use ordinary globs.

# The recorder names its files <something>_<date>_<time>A0.MP3; only that shape
# can be taken apart into the name we keep.
ingest_recorder_mp3(){
    local -a mp3files=("$INBOX_DIR"/*.MP3(N))
    local -a named_as_expected=("$INBOX_DIR"/*_*_*A0.MP3(N))

    echo_info "There are ${#mp3files} mp3 file(s)."
    if (( ${#named_as_expected} > 0 )); then
        zmv -v "$INBOX_DIR/*_(*)_(*)A0.MP3" "$RECORDER_DIR/\$1_\$2.MP3" \
            || count_failure "Failed to move recorder MP3 file(s) to $RECORDER_DIR."
    fi
    # Anything else stays in the inbox forever unless somebody is told about it.
    if (( ${#mp3files} > ${#named_as_expected} )); then
        count_failure "$(( ${#mp3files} - ${#named_as_expected} )) MP3 file(s) in $INBOX_DIR do not match *_*_*A0.MP3 and were left there."
    fi
}

# Voice memos arrive named after the app, not after the day they were recorded,
# so take the date out of the container metadata and put it in front.
ingest_voice_memos(){
    local -a m4afiles=("$INBOX_DIR"/*.m4a(N))
    local m4afile recording_date

    echo_info "There are ${#m4afiles} m4a file(s)."
    for m4afile in "${m4afiles[@]}"; do
        recording_date=$(ffprobe -loglevel quiet -of json -show_entries stream "$m4afile" \
            | jq -r '.streams[0].tags.creation_time' | cut -c 1-19 | sed 's/:/-/g')
        # An unreadable date would silently produce a "_name.m4a" that sorts
        # nowhere and hides the recording for good.
        if [[ -z "$recording_date" || "$recording_date" == "null" ]]; then
            count_failure "No creation_time in $m4afile, leaving it in $INBOX_DIR."
            continue
        fi
        mv -v "$m4afile" "$VOICEMEMO_DIR/${recording_date}_${m4afile:t}" \
            || count_failure "Failed to move $m4afile to $VOICEMEMO_DIR."
    done
}

# transcribe_directory <directory> <glob pattern> <files per run, 0 = all>
# Transcribes every file that has no .txt next to it yet.
transcribe_directory(){
    local dir=$1 pattern=$2 limit=$3
    local -a files
    local file
    local -i transcribed=0

    if [[ ! -d "$dir" ]]; then
        count_failure "Transcription directory not found: $dir"
        return 1
    fi

    nfd_safe_glob files "$dir" "$pattern"
    for file in "${files[@]}"; do
        [[ -e "${file:r}.txt" ]] && continue
        echo_info "Transcribing $file"
        if ! uv tool run parakeet-mlx --model "$PARAKEET_MODEL" "$file" --output-dir "$dir"; then
            count_failure "Transcription failed: $file"
            continue
        fi
        # parakeet writes SRT; keeping it as .txt is what makes the next run
        # skip this file.
        if ! mv "${file:r}.srt" "${file:r}.txt"; then
            count_failure "Transcript of $file was not written where expected."
            continue
        fi
        (( ++transcribed ))
        if (( limit > 0 && transcribed >= limit )); then
            echo_info "Transcribed $transcribed file(s); the rest wait for the next run."
            break
        fi
    done
    return 0
}

if [[ -d "$INBOX_DIR" ]]; then
    ingest_recorder_mp3
    ingest_voice_memos
else
    count_failure "$INBOX_DIR not found, nothing was ingested."
fi

echo_info "Starting transcription..."
transcribe_directory "$VOICEMEMO_DIR" "*.m4a" 0
transcribe_directory "$RECORDER_DIR" "*.MP3" $RECORDER_TRANSCRIPTS_PER_RUN

# Let maintain.sh's run_step know that something did not make it through.
routine_exit_status
