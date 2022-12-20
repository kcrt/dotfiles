#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  let_me_know_when_process_ends.sh
#
#         USAGE:  ./let_me_know_when_process_ends.sh name|pid
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

if [ $# -ne 1 ]; then
    echo "Usage: $0 name|pid"
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


