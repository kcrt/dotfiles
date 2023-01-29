#!/usr/bin/env zsh

hostname=${HOST:r}

TMa=`tmutil listbackups | sort -r | peco --prompt "Choose 1st one."`
TMb=`tmutil listbackups | sort -r | peco --prompt "Choose 2nd one."`

tmutil compare "$TMa" "$TMb" | less
