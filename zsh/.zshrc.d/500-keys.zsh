#
#	500-keys.zsh
#		Keybindings and vi mode functions
#

# ----- キー
bindkey -v
bindkey '^z'	push-line
bindkey "${terminfo[kf1]}" run-help  # F1
# viモードではあるが一部のemacsキーバインドを有効にする。
bindkey '^A'	beginning-of-line
bindkey '^E'	end-of-line
bindkey '^B'	backward-char
bindkey '^F'	forward-char
bindkey '^P'	up-line-or-history
bindkey '^N'	down-line-or-history
bindkey '^H'	vi-backward-delete-char

# ----- 自分用関数
function ShowStatus(){

	# モードの切り替え時に右上にモードを表示
	integer Cursor_X
	integer Cursor_Y
	integer StrLength
	StrLength=$(echo -n $1 | wc -m)
	Cursor_X=$[COLUMNS-$StrLength]	# 場所はお好みで
	Cursor_Y=1
	echo -n "\e7"				# Save cursor position
	# CSI echo -n "\e[s"			# push pos
	echo -n "\e[$[$Cursor_Y];$[$Cursor_X]H"	# set pos
	echo -n "\e[07;37m$1\e[m" # print
	# CSI echo -n "\e[u"			# pop pos
	echo -n "\e8"				# Restore cursor position

}
# viins <-> vicmd {{{
function Vi_ToCmd(){
	ShowStatus "-- NORMAL --"
	builtin zle .vi-cmd-mode
}
function Vi_Insert(){
	ShowStatus "-- INSERT --"
	builtin zle .vi-insert
}
function Vi_InsertFirst(){
	ShowStatus "-- INSERT --"
	builtin zle .vi-insert-bol
}
function Vi_AddNext(){
	ShowStatus "-- INSERT --"
	builtin zle .vi-add-next
}
function Vi_AddEol(){
	ShowStatus "-- INSERT --"
	builtin zle .vi-add-eol
}
function Vi_Change(){
	ShowStatus "-- INSERT --"
	builtin zle .vi-change
}
zle -N Vi_ToCmd
zle -N Vi_Insert
zle -N Vi_InsertFirst
zle -N Vi_AddNext
zle -N Vi_AddEol
zle -N Vi_Change
bindkey -M viins "\e" Vi_ToCmd
bindkey -M vicmd "i" Vi_Insert
bindkey -M vicmd "I" Vi_InsertFirst
bindkey -M vicmd "a" Vi_AddNext
bindkey -M vicmd "A" Vi_AddEol
bindkey -M vicmd "c" Vi_Change
bindkey -M vicmd "/" history-incremental-pattern-search-backward
bindkey '^R' history-incremental-pattern-search-backward
bindkey '^S' history-incremental-pattern-search-forward
bindkey "^Q" self-insert
# }}}

# ----- Plugin-specific keybindings
# zsh-history-substring-search
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down
bindkey -M vicmd 'k' history-substring-search-up
bindkey -M vicmd 'j' history-substring-search-down

# zsh-autosuggestions
ZSH_AUTOSUGGEST_STRATEGY=(history completion)
ZSH_AUTOSUGGEST_BUFFER_MAX_SIZE=20
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=8"
