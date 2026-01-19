#
#	090-hooks.zsh
#		Title updates, command time notifications
#

# ----- Hooks
function set_title(){

	local Title=$1
	if [[ $USER == "root" ]]; then
		# rootの場合**を付ける
		Title="*$Title*"
	fi

	if [[ $Title = "tmux" ]]; then
		# "tmux"と延々と表示されるのを防ぐ
		Title="$HOST"
	fi

	if [[ "$TERM_PROGRAM" == "tmux" ]]; then
		tmux rename-window "$Title"
	elif [[ -n "$ZELLIJ" ]]; then
		# zellij
		zellij action rename-tab "$Title" 2>/dev/null
		echo -n "\e]0;$Title\e\\"
	elif [[ -n $SSH_CLIENT ]]; then
		# via ssh
		echo -n "\e]2;$HOST:$Title\a"
	else
		echo -n "\e]0;$Title\e\\"
	fi

}

function ShowTitle_preexec(){

	# --- show title command
	local -a cmd
	local Title
	cmd=(${(z)2})
	case $cmd[1] in
		fg)
			if (( $#cmd == 1 )); then
				Title=(`builtin jobs -l %+`)
			else
				Title=(`builtin jobs -l $cmd[2]`)
			fi
			;;
		%*)
			# %1 = fg %1
			Title=(`builtin jobs -l $cmd[1]`)
			;;
		ls|pwd)
			Title=`dirs -p | sed -e"1p" -e"d"`
			;;
		cd|z|_z)
			Title=$cmd[2]
			;;
		sudo)
			if [[ "$cmd[2]" == "-E" ]]; then
				Title="*$cmd[3]*"
			else
				Title="*$cmd[2]*"
			fi
			;;
		ssh|ftp|telnet|mosh|mosh-client)
			Title="$cmd[1]:$cmd[2]";
			;;
		*)
			Title=$cmd[1];
			;;
	esac
	# if length of Title is larger than 15 chars, truncate it in "AAA...ZZZ" format
	if [[ ${#Title} -gt 15 ]]; then
		Title="${Title: 0:5}...${Title: -5:5}"
	fi
	set_title $Title

}

# FIXED: Moved COMMAND and COMMAND_TIME into global scope (they need to persist between hooks)
COMMAND=""
COMMAND_TIME="0"

function CheckCommandTime_preexec(){

	# --- notify long command
	COMMAND="$1"
	COMMAND_TIME=`date +%s`	# start time (Unix epoch)

}
function CheckCommandTime_precmd(){
	# Will execute before each prompt display

	# --- notify long command
	IsError=$?
	if [[ "$COMMAND_TIME" -ne "0" ]]; then
		local d=`date +%s`
		d=`expr $d - $COMMAND_TIME`
		# if the command takes more than 30 seconds, notify with terminal
		if [[ "$d" -ge "30" ]] ; then
			# ignore zsh, tmux, ssh, mosh
			if [[ "$COMMAND" =~ ^(zsh|tmux|ssh|mosh) ]]; then
				return
			fi

			# set COMMAND_INFO to
			#  $COMMAND without double quotes
			#  First 20 character
			local COMMAND_INFO=`echo $COMMAND | sed -e 's/^"//' -e 's/"$//' | cut -c 1-20`
			if [[ $IsError -ne 0 ]]; then
				OSError "$COMMAND_INFO" "took $d seconds and finally failed."
			else
				OSNotify "$COMMAND_INFO" "took $d seconds and finally finished."
			fi
			# if the command takes more than 30 minutes, notify with slack
			if [[ "$d" -ge "1800" ]]; then
				MIN=`expr $d / 60`
				SEC=`expr $d % 60`
				if [ $MIN -ge 60 ]; then
					HOUR=`expr $MIN / 60`
					MIN=`expr $MIN % 60`
					duration_str="$HOUR hours $MIN minutes $SEC seconds"
				else
					duration_str="$MIN minutes $SEC seconds"
				fi
				notify-slack "Command took $duration_str with $IsError: $COMMAND_INFO"
			fi
		fi

	fi
	COMMAND=""
	COMMAND_TIME="0"

}
add-zsh-hook preexec ShowTitle_preexec
add-zsh-hook precmd  CheckCommandTime_precmd
add-zsh-hook preexec CheckCommandTime_preexec

# Set initial title on startup
set_title "$(${DOTFILES}/script/host_and_connect.sh)"
