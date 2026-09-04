#
#	096-terminal_multiplexer.zsh
#		Zellij/tmux/screen session detection
#

if command -v zellij &> /dev/null; then
	if [[ -z "$ZELLIJ" ]]; then
		# Only show active sessions (filter out Exited sessions)
		# FIXED: Moved active_sessions into the if block where it's used
		local active_sessions=$(zellij ls 2>/dev/null | grep -v "EXITED" | grep -v "^$")
		if [[ -n "$active_sessions" ]]; then
			echo " --- zellij sessions --- "
			echo "$active_sessions"
			echo " ----------------------- "
		fi
	fi

	# 複数エージェント並走用セッションの起動 (layouts/agents.kdl)。
	# ZELLIJ_NO_TAB_RENAME は zellij サーバへ渡ってセッション内の全ペインに継承され、
	# set_title のタブ改名だけを抑止する。ペインタイトルの OSC は出るので、
	# 名前なしペインの枠には各エージェントの作業内容が出たままになる。
	function zellij-agents(){
		ZELLIJ_NO_TAB_RENAME=1 zellij -n agents "$@"
	}
elif command -v tmux &> /dev/null; then
	if [[ -z "$TMUX" ]]; then
		tmux ls
	fi
elif command -v screen &> /dev/null; then
	if [[ `expr $TERM : screen` -eq 0 ]]; then
		# sleep 1
		screen -r
	fi
else
	echo "screen not found."
fi
