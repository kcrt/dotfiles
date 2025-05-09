#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  let_me_know_when_process_ends.sh
#
#         USAGE:  ./let_me_know_when_process_ends.sh [--audio] name|pid
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

# Parse options
play_audio=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --audio)
            play_audio=true
            shift
            ;;
        *)
            break
            ;;
    esac
done

if [ $# -ne 1 ]; then
    echo "Usage: $0 [--audio] name|pid"
    echo "  --audio    Play audio notification when process ends"
    exit 1
fi

if [ -n "`echo $1 | grep '^[0-9]\+$'`" ]; then
    # $1 is a pid
    pid=$1
else
    # $1 is a name
    process_lists=`ps -ef | grep $1 | grep -v grep`
    if [ `echo $process_lists | wc -l` -eq 0 ]; then
        echo "No process found"
        exit 1
    elif [ `echo $process_lists | wc -l` -eq 1 ]; then
        echo "$process_lists"
        pid=`echo $process_lists | awk '{print $2}'`
    else
        pid=`echo $process_lists | peco | awk '{print $2}'`
    fi
fi

echo "Waiting for process $pid to end..."
while [ -n "`ps -ef | grep $pid | grep -v grep`" ]; do
    sleep 1
done

OSNotify "pid: $pid" "Process $1 was finished"

# Play audio notification if requested
if [ "$play_audio" = true ]; then
    if [ -f "${HOME}/dotfiles/audio/done.m4a" ]; then
        afplay --volume 0.5 "${HOME}/dotfiles/audio/done.m4a"
    else
        echo "Audio file not found: ${HOME}/dotfiles/audio/done.m4a"
    fi
fi
