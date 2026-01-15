#
#	068-functions_migemo.zsh
#		Migemo-based cd function
#

function mcd(){
	# Change directory with migemo
	if [ $# -eq 0 ]; then
		echo "example: `mcd iryou` will execute `cd 医療`"
	elif [ $# -eq 1 ]; then
		if [ "$(uname)" = "Darwin" ]; then
			migemolist=`cmigemo -d $($BIN_HOMEBREW --prefix)/Cellar/cmigemo/*/share/migemo/utf-8/migemo-dict -w "$1"`
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
			dirname=`echo "$dirname" | peco`
		fi
		echo "cd to $dirname"
		cd "$dirname"
	fi
}
