#!/bin/zsh

# show cpuload 1min
#   param
#		heavy | light

source ~/etc/script/echo_color.sh 

loadavg=`uptime | sed 's/.*load average.*: //' | sed 's/,/ /' | awk '{printf($1)}'`

if [[ -x `which osx-cpu-temp` ]]; then
	temp=`osx-cpu-temp | sed 's/°C/C/'`
	result="$loadavg $temp"
else
	result="$loadavg"
fi

if [[ "$1" == "heavy" && $loadavg -gt 6 ]]; then
	echo $result
elif [[ "$1" == "light" && $loadavg -le 6 ]]; then
	echo $result
elif [[ "$1" == "tmux" ]]; then
	if [[ $loadavg -gt 6 ]]; then
		echo "#[bg=red]$result#[default]"
	elif [[ $loadavg -gt 4 ]]; then
		echo "#[bg=color220, fg=black]$result#[default]"
	else
		echo "$result"
	fi
fi
