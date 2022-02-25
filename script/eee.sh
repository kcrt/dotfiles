#!/bin/zsh

autoload -U zmv
noglob zmv -n '([a-esgx])(\(*\) \[*\]*.zip)' '/Volumes/eee/comics/${(U)1}/$2'

~/etc/script/ask.sh -y "Are you sure?"

if [ $? -eq 0 ]; then
	noglob zmv -v '([a-esgx])(\(*\) \[*\]*.zip)' '/Volumes/eee/comics/${(U)1}/$2'
fi
