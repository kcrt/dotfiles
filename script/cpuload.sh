#!/bin/zsh

# show cpuload 1min
#   param
#		heavy | light | tmux

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0") [heavy|light|tmux]"
    echo "Displays CPU load average (1-minute) and temperature (if available)."
    echo ""
    echo "Arguments (optional):"
    echo "  heavy   - Only display if load average > 6."
    echo "  light   - Only display if load average <= 6."
    echo "  tmux    - Format output for tmux status bar with color coding based on load."
	echo "  zjstatus- Format output for zjstats with color coding based on load."
    echo "If no argument is given, displays load and temperature normally."
    exit 0
fi

source ~/dotfiles/script/echo_color.sh 

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
elif [[ "$1" == "zjstatus" ]]; then
	if [[ $loadavg -gt 6 ]]; then
		echo "#[bg=#d74242, fg=#F5E0E0]$result"
	elif [[ $loadavg -gt 4 ]]; then
		echo "#[fg=#D7A042]$result"
	else
		echo "#[fg=#eaf0f6]$result"
	fi
else
	echo $result
fi
