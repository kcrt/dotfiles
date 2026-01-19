#
#	068-functions_cd.zsh
#		cd family function
#

function mcd(){
	# Change directory with migemo
	# cmigemo -d /opt/homebrew/Cellar/cmigemo/20110227/share/migemo/utf-8/migemo-dict -w "iryou"
	# -> (ｲﾘｮｳ|イリョウ|衣[糧料]|医療|いりょう|ｉｒｙｏｕ|iryou)

	if [ $# -eq 0 ]; then
		echo "example: `mcd iryou` will execute `cd 医療`"
	elif [ $# -eq 1 ]; then
		if [ "$(uname)" = "Darwin" ]; then
			migemolist=`cmigemo -d /opt/homebrew/opt/cmigemo/share/migemo/utf-8/migemo-dict -w "$1"`
			dirname=`find . -maxdepth 1 -mindepth 1 -type d | iconv -f UTF-8-MAC -t UTF-8 | grep --color=never -E $migemolist`
		else
			migemolist=`cmigemo -d /usr/share/cmigemo/utf-8/migemo-dict -w "$1"`
			dirname=`find . -maxdepth 1 -mindepth 1 -type d | grep --color=never -E $migemolist`
		fi
		ndir=`echo "$dirname" | wc -l`
		if [ "$dirname" = "" ]; then
			echo "no such a directory."
			return 1
		elif [ $ndir -gt 1 ]; then
			dirname=`echo "$dirname" | fzf`
			if [ "$dirname" = "" ]; then
				echo "no directory selected."
				return 1
			fi
		fi
		echo "cd to $dirname"
		cd "$dirname"
	fi
}

function lcd(){
	# Find directory with mdfind and select with fzf, then cd to it
	if [ $# -eq 0 ]; then
		echo "example: `lcd 医療` will locate 医療 and execute `cd /path/to/医療`"
	elif [ $# -eq 1 ]; then
		dirname=`mdfind "kMDItemContentType='public.folder' && kMDItemFSName == '*$1*'c" | fzf --height 40% --layout=reverse --border`
		if [ "$dirname" = "" ]; then
			echo "no such a directory."
			return 1
		fi
		echo "cd to $dirname"
		cd "$dirname"
	fi
}