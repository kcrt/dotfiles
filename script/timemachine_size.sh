#!/usr/bin/env zsh

hostname=${HOST:r}
tmutil calculatedrift "`tmutil machinedirectory`" | less
