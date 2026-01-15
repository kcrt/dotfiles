#
#	099-finish.zsh
#		Zcompile, fortune, zprof
#

if [ ! -f ~/zshrc.zwc -o ~/.zshrc -nt ~/.zshrc.zwc ]; then
	# compile if modified
    zcompile ~/.zshrc
fi

# finally, execute fortune.
if [ -z "$BENCHMARK_ZSHRC" ] && command -v fortune &> /dev/null; then
	echo ""
	STARTUP_FORTUNE=`fortune`
	echo -n "\e[$color[$hostcolor]m"
	echo $STARTUP_FORTUNE
	if command -v ollama &> /dev/null; then
		echo -n "\e[2;97m"
		echo "Run \e[4mwhat_is_this_fortune\e[24m to know the meaning of this fortune."
		echo -n "\e[0m"
		echo ""
		function what_is_this_fortune(){
			ollama run "$OLLAMA_MY_DEFAULT_MODEL" "下記の文章を日本語で解説してください。\n$STARTUP_FORTUNE"
		}
	fi
fi

if command -v zprof > /dev/null 2>&1; then
	zprof
fi
