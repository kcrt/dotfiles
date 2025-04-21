
#
#	.zshrc
#		Written by kcrt <kcrt@kcrt.net>
#				Nanoseconds Hunter "http://www.kcrt.net"
#
#	参考:
#		http://nijino.homelinux.net/diary/200206.shtml#200206140
#		http://d.hatena.ne.jp/umezo/20100508/1273332857
#		http://www.clear-code.com/blog/2011/9/5.html
#		https://github.com/zplug/zplug/blob/master/doc/guide/ja/README.md

# To check loading time, run `bench-zsh`
if [[ -n "$BENCHMARK_ZSHRC" ]]; then
	function date_in_ms(){
		if [[ "$OSTYPE" = darwin* ]]; then
			gdate +%s%3N
		else
			date +%s%3N
		fi
	}
	start=$(date_in_ms)
	function end_of(){
		now=$(date_in_ms)
		# show elapsed time in ms with color (aqua)
		echo -e "\e[36m$1 done: $((now - start)) ms\e[m"
	}
else
	function end_of(){
		:	# do nothing
	}
	alias bench-zsh='time BENCHMARK_ZSHRC=1 zsh -i -c exit'
fi

# ----- load external files
if [[ -z "$DOTFILES" ]]; then
	echo "DOTFILES is not defined. Please define DOTFILES in .zshenv"
	return 1
fi
source ${DOTFILES}/script/OSNotify.sh
source ${DOTFILES}/script/echo_color.sh
source ${DOTFILES}/script/miscs.sh
if [ -f ${DOTFILES}/no_git/secrets.sh ]; then
	source ${DOTFILES}/no_git/secrets.sh
fi
end_of "source"

# ----- 環境変数
export LANG=ja_JP.UTF-8
export EDITOR="vim"
export COLOR="tty"
export GPG_TTY=$(tty)
export PYTHONSTARTUP=${DOTFILES}/pythonrc.py
export GOOGLE_APPLICATION_CREDENTIALS="`echo ~/secrets/kcrtjp-google-serviceaccount.json`"
stty stop undef					# ^Sとかを無効にする
end_of "environment variables"

# ----- ホスト毎にプロンプト色の変更
# not all terminals support this
typeset -A hostcolors
typeset -A hostblacks
# Remote server: cyan, cloud machine: yellow,
# Local main machine: blue, Local sub machine: yellow
hostcolors=(
	kcrt.net cyan
	rctstudy.jp cyan
	lithium yellow
	aluminum blue aluminum.local blue
	beryllium yellow beryllium.local yellow
)
hostblacks=(
	kcrt.net 001111
	rctstudy.jp 001111
	lithium 001111
	aluminum 000011 aluminum.local 000011
	beryllium 001111 beryllium.local 001111
)
if (( ${hostcolor[(i)${HOST}]} )); then
	# Not found: Default color
	hostcolor="magenda"
	hostblack="000000"
else
	hostcolor=$hostcolors[$HOST]
	hostblack=$hostblacks[$HOST]
fi
if [[ "$TERM" == (screen*|xterm*) && "$SSH_CONNECTION" == "" ]]; then
	# Set palette color
	# ␛](OSC) P n rr gg bb ␛\(ST)
	echo -n "\e]R\e\\"				# first, reset the palette
	echo -n "\e]P0${hostblack}\e\\"	# black
	echo -n "\e]P1FF0000\e\\"		# red
	echo -n "\e]P200CC00\e\\"		# green
	echo -n "\e]P3CCCC00\e\\"		# yellow
	echo -n "\e]P461A1E5\e\\"		# blue
	echo -n "\e]P5FF00FF\e\\"		# magenta
	echo -n "\e]P600FFFF\e\\"		# cyan
	echo -n "\e]P7CCCCCC\e\\"		# white
	echo -n "\e]P8676767\e\\"		# BLACK
	echo -n "\e]P9FFAAAA\e\\"		# RED
	echo -n "\e]PA88FF88\e\\"		# GREEN
	echo -n "\e]PBFFFFAA\e\\"		# YELLOW
	echo -n "\e]PC7777FF\e\\"		# BLUE
	echo -n "\e]PDFFCCFF\e\\"		# MAGENTA
	echo -n "\e]PE88FFFF\e\\"		# CYAN
	echo -n "\e]PFFFFFFF\e\\"		# WHITE
fi
end_of "hostcolor"

# ----- タイトルバーの文字列
# ␛](OSC) 0; _title_ ␛\(ST)
local title
if [[ "$SSH_CONNECTION" != "" ]]; then
	# ssh接続
	title="$HOST (`echo -n $SSH_CONNECTION | sed -e 's/\(.*\) .* \(.*\) .*/\1 --> \2/g'`, ssh)"
elif [[ "$REMOTEHOST" != "" ]]; then
	# おそらくtelnet
	title="$REMOTEHOST --> $HOST";
elif [[ "$OSTYPE" == "cygwin" ]]; then
	# cygwin
	title="$HOST (cygwin)";
else
	# 普通のローカル
	title="$HOST (local)";
fi
echo -n "\e]2;${title}\e\\"
end_of "titlebar"

# ----- 色関係
autoload colors					# $color[red]とかが使えるようになる。
colors
if [[ -x dircolors ]]; then
	eval `dircolors -b`
fi
export ZLS_COLORS=$LS_COLORS
export CLICOLOR=true
end_of "colors"

# ----- homebrew
# check arch to determine place of homebrew
if [[ "$OSTYPE" = darwin* ]]; then
	if [[ "$(uname -m)" = "arm64" ]]; then
		export BIN_HOMEBREW="/opt/homebrew/bin/brew"
	elif [[ "$(uname -m)" = "x86_64" ]]; then
		export BIN_HOMEBREW="/usr/local/bin/brew"
	fi
	alias brew="$BIN_HOMEBREW"
	
	# Load homebrew completions early to avoid conflicts
	if [[ -d "$($BIN_HOMEBREW --prefix)/share/zsh/site-functions" ]]; then
		FPATH="$($BIN_HOMEBREW --prefix)/share/zsh/site-functions:${FPATH}"
	fi
fi

# ----- autoloadたち
autoload -Uz is-at-least		# versionによる判定
# autoload -U +X bashcompinit && bashcompinit
if [[ -d "$HOME/.cargo" && -x "$HOME/.cargo/bin/rustc" ]]; then
	CARGO_COMPLETION="`$HOME/.cargo/bin/rustc --print sysroot 2>/dev/null`/share/zsh/site-functions"
	if [[ -d "$CARGO_COMPLETION" ]]; then
		FPATH="$CARGO_COMPLETION:${FPATH}"
	fi
fi
if [[ $UID -ne 0 ]]; then
	# Only regenerate completions once per day
	autoload -Uz compinit
	if [[ -n "$ZSH_COMPDUMP" ]]; then
		compinit -d "$ZSH_COMPDUMP"
	else
		ZSH_COMPDUMP="${ZDOTDIR:-$HOME}/.zcompdump-${ZSH_VERSION}"
		if [[ -f "$ZSH_COMPDUMP" && $(date +'%j') != $(stat -f '%Sm' -t '%j' "$ZSH_COMPDUMP") ]]; then
			compinit -d "$ZSH_COMPDUMP"
		else
			compinit -C -d "$ZSH_COMPDUMP"
		fi
	fi
fi
autoload zmv
autoload zargs
autoload zsh/files
autoload -Uz url-quote-magic
if [[ -f /etc/zsh_command_not_found ]]; then
	source /etc/zsh_command_not_found
fi
end_of "autoload"


# ----- 補完
LISTMAX=200							# 表示する最大補完リスト数
setopt auto_list					# 曖昧な補完で自動的にリスト表示
setopt NO_menu_complete				# 一回目の補完で候補を挿入(cf. auto_menu)
setopt auto_menu					# 二回目の補完で候補を挿入
setopt magic_equal_subst			# --include=/usr/... などの=補完を有効に
setopt NO_complete_in_word			# カーソル位置で補完する
setopt list_packed					# 補完候補をできるだけつめて表示する
setopt NO_list_beep					# 補完候補表示時にビープ音を鳴らす
setopt list_types					# ファイル名のおしりに識別マークをつける

# Advanced completion configuration
zstyle ':completion:*' format '%B%d%b'
zstyle ':completion:*' group-name ''	# 補完候補をグループ化する
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}	# 補完も色つける
zstyle ':completion:*' use-cache yes
zstyle ':completion:*' cache-path "${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zcompcache"
zstyle ':completion:*' completer _expand _complete _ignored _approximate
zstyle ':completion:*' matcher-list '' 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=*' 'l:|=* r:|=*'
zstyle ':completion:*' verbose yes 	# 詳細な情報を使う。
zstyle ':completion:sudo:*' environ PATH="$SUDO_PATH:$PATH" # sudo時にはsudo用のパスも使う。
zstyle ':completion:*:default' menu select=2
zstyle ':completion:*:processes' command 'ps x -o pid,args'	# kill <tab>での補完
zstyle ':completion:*:*:*:*:*' menu select
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#) ([0-9a-z-]#)*=01;34=0=01'



# ----- 履歴
HISTFILE="$HOME/.zhistory"			# 履歴保存先
HISTSIZE=100000						# 使用する履歴数
SAVEHIST=100000						# 保存する履歴数
setopt hist_ignore_space			# スペースで始まるコマンドを記録しない
setopt hist_ignore_all_dups			# 重複した履歴を記録しない
setopt hist_find_no_dups			# 履歴検索中に重複を飛ばす
setopt hist_save_no_dups			# 重複するコマンドを保存しない
setopt hist_reduce_blanks			# 余分な空白を削除して保存
setopt share_history				# ターミナル間の履歴を共有する
setopt append_history				# 履歴を追記する
setopt inc_append_history			# 履歴をすぐに追記する

# ----- ファイル操作関連
setopt auto_cd						# ディレクトリ名でcd
setopt auto_remove_slash			# 不要なスラッシュをはずす
setopt auto_pushd					# 自動的にpushd
setopt pushd_ignore_dups			# 重複したディレクトリスタックを記録しない
setopt correct						# コマンドのスペル補正
setopt correct_all					# コマンド以外もスペル補正
CORRECT_IGNORE_FILE='.*'
setopt equals						# =zshとかが置換される
setopt extended_glob				# 拡張グロブ有効
# ----- そのほかの設定
setopt prompt_subst					# プロンプトでのコマンド置換などを有効に
setopt beep							# エラー時にはBeep音
setopt notify						# バックグラウンドジョブの状態変化を報告
setopt NO_emacs						# viが一番！
setopt NO_flow_control				# ^S/^Qを有効にするかどうか
disable r							# r (再実行コマンド)を無効にする
end_of "setopt"

# ----- Japanese, Wide Char set, and Unicode
setopt print_eight_bit				# 8ビット文字表示
function print_test(){
	echo "ASCII: ABCDEFGabcdefg"
	echo "Japanese: 本日は晴天なり。"
	echo "Symbol: ○△□●▲■◎＋ー×÷※"
	echo "Symbol: [][][][][][][][][][][][]"
	echo "Symbol: 〠♫✔✘✂✰"
	echo "Symbol: 😄😊😃👌👎🇯🇵"
	echo "Symbol: [☺️]"
	echo "Color: " -n
	for i in {16..21} {21..16} ; do echo -en "\e[38;5;${i}m#\e[0m" ; done ; echo
}

# ----- zplug
if [[ -r ~/.zplug/init.zsh ]]; then
	source ~/.zplug/init.zsh
	
	# Essential plugins
	zplug "zsh-users/zsh-syntax-highlighting", defer:2
	zplug "zsh-users/zsh-history-substring-search", defer:2
	zplug "zsh-users/zsh-completions", defer:2
	zplug "zsh-users/zsh-autosuggestions", defer:2
	
	# Conditional plugins
	if [[ -n "$BIN_HOMEBREW" ]]; then
		zplug "plugins/brew", from:oh-my-zsh, defer:2
	fi
	
	# Navigation and utility plugins
	zplug "rupa/z", use:z.sh, defer:2
	zplug "b4b4r07/enhancd", use:init.sh, defer:2
	zplug "momo-lab/zsh-abbrev-alias", defer:2
	
	end_of "zplug 1"
	export ENHANCED_FILTER=fzy:fzf:peco
	
	# Install plugins if not already installed
	if ! zplug check; then
		printf "Install missing zplug plugins? [y/N]: "
		if read -q; then
			echo; zplug install
		fi
	fi
	
	zplug load
	end_of "zplug 2"
	
	# Configure zsh-history-substring-search keybindings
	if zplug check "zsh-users/zsh-history-substring-search"; then
		bindkey '^[[A' history-substring-search-up
		bindkey '^[[B' history-substring-search-down
		bindkey -M vicmd 'k' history-substring-search-up
		bindkey -M vicmd 'j' history-substring-search-down
	fi
	
	# Configure zsh-autosuggestions
	if zplug check "zsh-users/zsh-autosuggestions"; then
		ZSH_AUTOSUGGEST_STRATEGY=(history completion)
		ZSH_AUTOSUGGEST_BUFFER_MAX_SIZE=20
		ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=8"
	fi
else
	echo "Please execute 'curl -sL --proto-redir -all,https https://raw.githubusercontent.com/zplug/installer/master/installer.zsh | zsh' to install zplug"
	function abbrev-alias(){
		# skip this command
	}
fi

# ----- Version Control(svn, git)のブランチなどを表示
RPROMPT=""
if is-at-least 4.3.7; then
	autoload -Uz vcs_info
	autoload -Uz add-zsh-hook
	# formats: 平時用、actionformats: merge conflictなど特殊な状況
	# %s -> VCS in use, %b -> branch, %a -> action
	zstyle ':vcs_info:*' formats '%s: %b%c%u'
	zstyle ':vcs_info:*' actionformats '%s: %b%c%u[%a]'
	# git
	if is-at-least 4.3.10; then
		zstyle ':vcs_info:git:*' check-for-changes true
		zstyle ':vcs_info:git:*' stagedstr "📌"
		zstyle ':vcs_info:git:*' unstagedstr "📝"
	fi
	precmd_vcs_info () {
		psvar=()
		LANG=en_US.UTF-8 vcs_info
		[[ -n "$vcs_info_msg_0_" ]] && psvar[1]="$vcs_info_msg_0_"
	}
	add-zsh-hook precmd precmd_vcs_info
	RPROMPT="%1(v|%F{green}%1v%f|)"
fi
end_of "gitinfo"

# ----- プロンプト
if [[ $UID -eq 0 ]]; then
	PROMPT_COLOR="%F{red}"
else
	PROMPT_COLOR="%F{$hostcolor}"
fi
# is on tmux ?
SUBSTLV=$SHLVL
if [[ "$TERM_PROGRAM" = "vscode" ]]; then
	SUBSTLV=$[SUBSTLV-3]
elif [[ -n "$TMUX" ]]; then
	SUBSTLV=$[SUBSTLV-1]
fi
if [[ $SUBSTLV -gt 1 ]]; then
	for (( i=2; i<=$SUBSTLV; i++ )); do
		PROMPT_SUBSTLV="${PROMPT_SUBSTLV}>"
	done
	PROMPT_SUBSTLV="%B${PROMPT_SUBSTLV}%b"
else
	PROMPT_SUBSTLV=""
fi
PROMPT_USER='%n'
PROMPT_HOST='${${${(%):-%M}%%.local}%.kcrtjp.internal}'
if [[ -x ${DOTFILES}/script/have_mail.sh ]]; then
	PROMPT_MAILCHECK='$(~/dotfiles/script/have_mail.sh)'
else
	PROMPT_MAILCHECK=''
fi
PROMPT_SHARP=' %# '
PROMPT_RESETCOLOR='%{$reset_color%}'
PROMPT="${PROMPT_SUBSTLV}${PROMPT_COLOR}[${PROMPT_USER}@${PROMPT_HOST}]${PROMPT_MAILCHECK}${PROMPT_SHARP}${PROMPT_RESETCOLOR}"

# 最後に実行したプログラムがエラーだと反転するよ。
RPROMPT_BGJOB='%(1j.(bg: %j).)'
RPROMPT_SETCOLOR=' %{%(?.$fg[cyan].$bg[cyan]$fg[black])%}'
RPROMPT_DIR=' [%(5~|%-2~/.../%2~|%~)] '
RPROMPT_PLATFORM='($(uname -m)) '
RPROMPT="${RPROMPT}${RPROMPT_BGJOB}${RPROMPT_SETCOLOR}${RPROMPT_DIR}${RPROMPT_PLATFORM}${PROMPT_RESETCOLOR}"

# ----- キー
bindkey -v
bindkey '^z'	push-line
bindkey 'OP'	run-help	# F1
bindkey -r ',' # unbind
bindkey -r '/'
# viモードではあるが一部のemacsキーバインドを有効にする。
bindkey ''	beginning-of-line
bindkey ''	end-of-line
bindkey ''	backward-char
bindkey ''	forward-char
bindkey ''	up-line-or-history
bindkey ''	down-line-or-history
bindkey ''	vi-backward-delete-char
end_of "bindkey"

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
	# CSI echo -n "[s"			# push pos
	echo -n "\e[$[$Cursor_Y];$[$Cursor_X]H"	# set pos
	echo -n "\e[07;37m$1\e[m" # print
	# CSI echo -n "[u"			# pop pos
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
bindkey -M viins "" Vi_ToCmd
bindkey -M vicmd "i" Vi_Insert
bindkey -M vicmd "I" Vi_InsertFirst
bindkey -M vicmd "a" Vi_AddNext
bindkey -M vicmd "A" Vi_AddEol
bindkey -M vicmd "c" Vi_Change
zle -la history-incremental-pattern-search-backward
zle -la history-incremental-pattern-search-forward
bindkey -M vicmd "/" history-incremental-pattern-search-backward
bindkey '^P' history-incremental-pattern-search-backward
bindkey '^N' history-incremental-pattern-search-forward
bindkey "^Q" self-insert
# }}}
end_of "vi mode key"


# ----- パス
typeset -U path PATH
# Add paths only if they exist
[[ -d "$HOME/.deno/bin" ]] && path=("$HOME/.deno/bin" $path)
[[ -n "$GOPATH" && -d "$GOPATH/bin" ]] && path=($path "$GOPATH/bin")
[[ -d "$HOME/.cargo/bin" ]] && path=($path "$HOME/.cargo/bin")
[[ -d "/snap/bin" ]] && path=($path "/snap/bin")
[[ -d "$HOME/bin" ]] && path=($path "$HOME/bin")

# ----- 関数
function _w3m(){
	W3MOPT=
	IsScreen=`expr $TERM : screen`
	if [[ $IsScreen != 0 ]]; then
		W3MOPT=-no-mouse
	fi
	:title w3m $1
	if [[ $1 == "" ]]; then
		\w3m $W3MOPT http://www.google.co.jp
	else
		\w3m $W3MOPT $@
	fi
	:title $SHELL
}
function testarchive(){
	if [[ ${1:e} = "zip" ]]; then
		zip -T $1
	elif [[ ${1:e} = "rar" ]]; then
		unrar t $1
	fi
}
function testallarchive(){
	for i in *.(zip|rar|lzh); do;
		testarchive $i
	done;
}
function backupnethack(){
	DATETIME=`date +"%Y%m%d_%H%M%S"`
	cp /usr/local/Cellar/nethacked/1.0/libexec/save/501kcrt.Z ~/backup/nethacked-backup-${DATETIME}-501kcrt.Z
}
function python_update() {
	if [[ -x conda ]]; then
		conda update conda
		conda update anaconda
		conda update --all
	fi
	pip install --upgrade pip
	pip freeze --local | grep -v '^\-e' | cut -d = -f 1 | xargs pip install --upgrade
}
end_of "function definitions"

# ----- エイリアス
# コマンド置き換え
abbrev-alias vi='vim -p'
abbrev-alias vimtree='vim -c "let g:nerdtree_tabs_open_on_console_startup = 1"'
abbrev-alias gvimtree='gvim -c "let g:nerdtree_tabs_open_on_console_startup = 1"'
abbrev-alias vimrc='vim ~/.vimrc'
abbrev-alias zshrc='vim ~/.zshrc'
# abbrev-alias rm='trash'
abbrev-alias mv='nocorrect mv'
abbrev-alias cp='nocorrect cp'
abbrev-alias mkdir='nocorrect mkdir'
abbrev-alias w3m=' noglob _w3m'
abbrev-alias exstrings='${DOTFILES}/script/exstrings.sh'
abbrev-alias mutt='neomutt'
abbrev-alias pv='pv -pterabT -i 0.3 -c -N Progress'

# Load command if available
if [[ -x "$(command -v thefuck)" && -z "$THEFUCK_LOADED" ]]; then
    export THEFUCK_LOADED=1
    eval "$(thefuck --alias)"
fi
# TODO: croc
# Check if croc command exists, if not, define a function using Docker
if ! command -v croc &> /dev/null; then
    function croc() {
        docker run -it --rm -w "$(pwd)" -v "$(pwd):$(pwd)" thecatlady/croc "$@"
    }
fi

abbrev-alias ssh-sign="ssh-keygen -Y sign -f ~/.ssh/kcrt-ssh-ed25519.pem -n file"
# 引数
if [[ "$OSTYPE" = darwin* || $OSTYPE = freebs* ]]; then
	alias ls='ls -FG'
	alias la='ls -FG -a'
	alias ll='ls -FG -la -t -r -h'
else
	alias ls='ls -F --color=auto'
	alias la='ls -F -a --color=auto'
	alias ll='ls -F -la -t -r --human-readable --color=auto'
fi
abbrev-alias du='\du -hcs *'
abbrev-alias df='df -H'
if [ -f /usr/share/vim/vimcurrent/macros/less.sh ]; then
	alias less=/usr/share/vim/vimcurrent/macros/less.sh
elif [ -f /usr/share/vim/vim*/macros/less.sh ]; then
	alias less='`\ls /usr/share/vim/vim*/macros/less.sh`'
else
	alias less='less --ignore-case --status-column --prompt="?f%f:(stdin).?m(%i/%m files?x, next %x.). ?c<-%c-> .?e(END):%lt-%lb./%Llines" --hilite-unread --tabs=4 --window=-5'
fi
alias pstree='pstree -p'
alias zmv='noglob zmv'
alias zcp='noglob zmv -C'
alias zln='noglob zmv -L'
alias history='history -E 1'
abbrev-alias wget='noglob wget'
abbrev-alias ping='ping -a -c4'
abbrev-alias ping6='ping6 -a -c4'
#abbrev-alias monitor_network='gping --watch-interval 2 --buffer 120 --color=green,blue,yellow profile.kcrt.net 8.8.8.8 192.168.0.1'
abbrev-alias monitor_network='sudo trip --geoip-mmdb-file ~/GeoLite2-City.mmdb --tui-geoip-mode short profile.kcrt.net 8.8.8.8'
alias sudo='sudo -E '	#スペースを付けておくとsudo llなどが使える
alias ag='ag -S'
alias grep='grep --color=auto --binary-file=without-match --exclude-dir=.git --exclude-dir=.svn'
alias dstat='sudo dstat -t -cl --top-cpu -m -d --top-io -n'
abbrev-alias wget-recursive="noglob wget -r -l5 --convert-links --random-wait --restrict-file-names=windows --adjust-extension --no-parent --page-requisites --quiet --show-progress -e robots=off"
abbrev-alias youtube-dl='noglob yt-dlp'
abbrev-alias whisper-jp="whisper --language Japanese --model large --device mps"
abbrev-alias mlx_whisper-jp='mlx_whisper --language Japanese --model "mlx-community/whisper-large-v3-turbo" --output-format vtt'
abbrev-alias parallel="parallel --bar -j8"
function ffmpeg_gif(){
	ffmpeg -i "$1" -an -r 15 -pix_fmt rgb24 -f gif "${1:t:r}.gif"
}
function ffmpeg_deinterlaced_mp4(){
	ffmpeg -i "$1" -vf "yadif=0:-1" -pix_fmt yuv420p "${1:t:r}.mp4"
}
function ffmpeg_480p_16:9_h264(){
	ffmpeg -i "$1" -vf scale=854:480 -c:v libx264 "${1:t:r} [480p h264].mp4"
}
function ffmpeg_480p_16:9_hevc(){
	ffmpeg -i "$1" -vf scale=854:480 -c:v libx265 "${1:t:r} [480p hevc].mp4"
}
function ffmpeg_480p_16:9_hevc_anime(){
	ffmpeg -i "$1" -vf scale=854:480 -c:v libx265 -tune animation "${1:t:r} [480p hevc].mp4"
}
function ffmpeg_720p_h264(){
	ffmpeg -i "$1" -vf scale=-1:720 -c:v libx264 "${1:t:r} [720p h264].mp4"
}
function ffmpeg_720p_hevc(){
	ffmpeg -i "$1" -vf scale=-1:720 -c:v libx265 "${1:t:r} [720p hevc].mp4"
}
function ffmpeg_720p_hevc_anime(){
	ffmpeg -i "$1" -vf scale=-1:720 -c:v libx265 -tune animation "${1:t:r} [720p hevc].mp4"
}
function ffmpeg_720p_av1(){
	ffmpeg -i "$1" -vf scale=-1:720 -c:v libsvtav1 "${1:t:r} [720p av1].mp4"
}
function ffmpeg_1080p_h264(){
	height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "$1")
	if [ "$height" -lt 1080 ]; then
		echo "height is less than 1080"
		return 1
	fi
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libx264 "${1:t:r} [1080p h264].mp4"
}
function ffmpeg_1080p_hevc_high_quality(){
	height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "$1")
	if [ "$height" -lt 1080 ]; then
		echo "height is less than 1080"
		return 1
	fi
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libx265 -x265-params crf=20 "${1:t:r} [1080p hevc].mp4"
}
function ffmpeg_1080p_hevc_default_quality(){
	height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "$1")
	if [ "$height" -lt 1080 ]; then
		echo "height is less than 1080"
		return 1
	fi
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libx265 "${1:t:r} [1080p hevc].mp4"
}
function ffmpeg_1080p_av1_default_quality(){
	height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "$1")
	if [ "$height" -lt 1080 ]; then
		echo "height is less than 1080"
		return 1
	fi
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libsvtav1 "${1:t:r} [1080p av1].mp4"
}
function ffmpeg_1080p_av1_high_quality(){
	height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=s=x:p=0 "$1")
	if [ "$height" -lt 1080 ]; then
		echo "height is less than 1080"
		return 1
	fi
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libsvtav1 -crf 23 "${1:t:r} [1080p av1 crf23].mp4"
}
function use_for_regza(){
	ffmpeg -i "$1" -f mpegts -c:v libx265 -c:a aac "/Volumes/REGZA/${1:t:r}.ts"
}
function use_for_regza_withoutconvert(){
	ffmpeg -i "$1" -f mpegts -vcodec copy -acodec copy "/Volumes/REGZA/${1:t:r}.ts"
}
function ffmpeg_maximize(){
	MAXVOL=`ffmpeg -i "$1" -vn -af volumedetect -f null - 2>&1 | grep max_volume | sed "s/.*max_volume: -//" | sed "s/ dB//"`
	ffmpeg -i "$1" -af volume=${MAXVOL}dB "${1:t:r}_maximized.${1:e}"
}

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
# 省略とか
abbrev-alias hist='history'
abbrev-alias :q='exit'
abbrev-alias su='su -s =zsh'
abbrev-alias od='od -Ax -tx1 -c'
abbrev-alias hexdump="hexdump -C"
abbrev-alias hex2bin="xxd -r -p"
abbrev-alias beep='print "\a"'
abbrev-alias cls='clear'
abbrev-alias ...='cd ../..'
abbrev-alias ....='cd ../../..'
abbrev-alias .....='cd ../../../..'
function vimman(){
	vim -c "Man $1" -c "only"
}
abbrev-alias man='vimman'
abbrev-alias clang++11='clang++ -O --std=c++11 -Wall --pedantic-errors --stdlib=libc++'
abbrev-alias clang++14='clang++ -O --std=c++14 -Wall --pedantic-errors --stdlib=libc++'
abbrev-alias clang++17='clang++ -O --std=c++17 -Wall --pedantic-errors --stdlib=libc++'
abbrev-alias clang++20='clang++ -O --std=c++20 -Wall --pedantic-errors --stdlib=libc++'
abbrev-alias eee='noglob zmv -v "([a-e|s|g|x])(*\(*\) \[*\]*).zip" "/Volumes/eee/comics/\${(U)1}/\$2.zip"'
abbrev-alias textlintjp="textlint --preset preset-japanese --rule spellcheck-tech-word --rule joyo-kanji --rule @textlint-rule/textlint-rule-no-unmatched-pair"
abbrev-alias decryptpdf="gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=unencrypted.pdf -c 3000000 setvmthreshold -f"
abbrev-alias pdb="`which env` python -m pdb"

abbrev-alias docker_busybox="docker run -it --rm busybox"
abbrev-alias docker_busybox_mount_home="docker run -it --rm -v $HOME:/root busybox"
abbrev-alias docker_alpine="docker run -it --rm alpine"
abbrev-alias docker_alpine_mount_home="docker run -it --rm -v $HOME:/root alpine"
abbrev-alias docker_ubuntu="docker run -it --rm ubuntu"
abbrev-alias docker_ubuntu_x86="docker run -it --platform linux/amd64 --rm ubuntu"
abbrev-alias docker_ubuntu_mount_home="docker run -it --rm -v $HOME:/root ubuntu"
abbrev-alias docker_mykali="docker build --tag mykali ${DOTFILES}/docker/mykali/; docker run -it --rm --hostname='mykali' --name='mykali' -v ~/.ssh/:/home/$USER/.ssh/:ro -v ${DOTFILES}/:/home/$USER/dotfiles:ro mykali"
abbrev-alias docker_myubuntu="docker build --tag myubuntu ${DOTFILES}/docker/myubuntu/; docker run -it --rm --hostname='myubuntu' --name='myubuntu' -v ~/.ssh/:/home/$USER/.ssh/:ro -v $HOME:/mnt/home myubuntu"
abbrev-alias docker_secretlint='docker run -v `pwd`:`pwd` -w `pwd` --rm -it secretlint/secretlint secretlint "**/*"'
abbrev-alias docker_carbonyl='docker run -ti fathyb/carbonyl --rm '
abbrev-alias docker_lazydocker='docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock -v /yourpath:/.config/jesseduffield/lazydocker lazyteam/lazydocker'

export WINEPREFIX="$HOME/.wine"
if [[ $OSTYPE = *darwin* ]] ; then
	abbrev-alias wine_steam="wine64 ~/.wine/drive_c/Program\ Files\ \(x86\)/Steam/Steam.exe -no-cef-sandbox"
	abbrev-alias wine_gameportingkit="LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8 MTL_HUD_ENABLED=1 WINEESYNC=1 `arch -x86_64 brew --prefix game-porting-toolkit`/bin/wine64"
fi
abbrev-alias oj_test_python="oj test -c './main.py' -d tests"
# one liner
abbrev-alias :svnsetkeyword='svn propset svn:keywords "Id LastChangeDate LastChangeRevision LastChangeBy HeadURL Rev Date Author"'
abbrev-alias :checkjpeg='find . -name "*.jpg" -or -name "*.JPG" -exec jpeginfo -c {} \;'
abbrev-alias :howmanyfiles='find . -print | wc -l'
abbrev-alias serve_http_here='python3 -m http.server'

abbrev-alias openai_image='openai api image.create -n 1 -p'
abbrev-alias openai_chatgpt='openai api chat_completions.create -m o1-preview --max-tokens 3500 -g user'
function openai_whatisthisfile(){
	FILENAME="$1"
	FILESIZE=`wc -c < "$FILENAME"`
	if [ $FILESIZE -ge 2048 ]; then
		echo "File too large."
	else
		openai api chat_completions.create -m o1-preview --max-tokens 1000 -g user "$(cat <(echo "下記のファイルの内容を説明してください。"; echo '```'; cat "$1"; echo '```'; ))"
	fi
}
abbrev-alias ollama-llama3.1='ollama run llama3.1:latest'
abbrev-alias ollama-llama3.2='ollama run llama3.2:latest'
abbrev-alias ollama-jp='ollama run 7shi/tanuki-dpo-v1.0'
abbrev-alias ollama-update="ollama list | tail -n +2 | tr -s ' ' | cut -d ' ' -f1 | xargs -n1 ollama pull"


# global alias
alias -g N='; OSNotify "shell" "operation finished"'

# 思い出し用
for f in `find ${DOTFILES}/sheet -maxdepth 1 -mindepth 1 -type f`; do
	alias :howto${f:t}="cat `realpath $f`"
done

# scriptフォルダ
for f in ${DOTFILES}/script/*; do
	alias ${f:t:r}="$f"
done

# bin
if [ -x ~/bin/imgcat ]; then
	alias imgcat="~/bin/imgcat"
fi

# 便利コマンド
abbrev-alias dirsizeinbyte="find . -type f -print -exec wc -c {} \; | awk '{ sum += \$1; }; END { print sum }'"
abbrev-alias finddups="find * -type f -exec shasum \{\} \; | sort | tee /tmp/shasumlist | cut -d' ' -f 1 | uniq -d > /tmp/duplist; while read DUPID; do grep \$DUPID /tmp/shasumlist; done < /tmp/duplist"
abbrev-alias iconv-nfdtonfc="iconv -f UTF-8-MAC -t UTF-8"
abbrev-alias iconv-nfctonfd="iconv -f UTF-8 -t UTF-8-MAC"
abbrev-alias verynice="nice -n 20"

# ----- suffix alias ()
alias -s exe='wine_gameportingkit'
alias -s txt='less'
alias -s log='tail -f -n20'
alias -s html='w3m'
function viewxls(){
	w3m -T text/html =(xlhtml $1)
}
alias -s png='imgcat'
alias -s jpg='imgcat'
alias -s md='glow -p'
alias -s json='jq -C .'

# ----- コマンドライン引数
#export GREP_OPTIONS='--color=auto --binary-file=without-match --line-number --exclude-dir=.git --exclude-dir=.svn'
# ----- Azure
alias azure_neon_start="az vm start --resource-group neon_group --name neon"
alias azure_neon_stop="az vm stop --resource-group neon_group --name neon; az vm deallocate --resource-group neon_group --name neon"

# ----- root以外用の設定
if [[ $USER != 'root' ]] ; then
	alias updatedb="sudo updatedb; beep"
fi

alias :package_update="${DOTFILES}/maintain.sh"

if [[ -x /usr/bin/yum ]] ; then
	alias :package_update="sudo yum update"
	alias :package_install="sudo yum install"
	alias :package_file="yum provides"
elif [[ -x /usr/bin/apt ]] ; then
	alias :package_update="sudo apt update; sudo apt upgrade"
	alias :package_install="sudo apt install"
	alias :package_list=""
	alias :package_search="sudo apt show"
	alias :package_file="apt-file search"
fi
end_of "alias definitions"


# ----- Fedora 固有設定
# alias :suspend="sudo /usr/sbin/pm-suspend"
# alias :hibernate="sudo /usr/sbin/pm-hibernate"

# ----- cygwin 固有設定
if [[ $OSTYPE = *cygwin* ]] ; then
	alias updatedb="updatedb --prunepaths='/cygdrive /proc'"
	alias open='cmd /c start '
	alias start='explorer . &'
fi

# ----- MacOS 固有設定
if [[ $OSTYPE = *darwin* ]] ; then
	# Set up man path if it exists
	[[ -d "/opt/local/man" ]] && export MANPATH=/opt/local/man:$MANPATH

	# Add LLVM and Android tools to path if they exist
	[[ -d "/usr/local/opt/llvm/bin" ]] && path=("/usr/local/opt/llvm/bin" $path)
	[[ -d "$HOME/Library/Android/sdk/platform-tools" ]] && path=($path "$HOME/Library/Android/sdk/platform-tools")
	
	# Set up Homebrew environment
	if [[ -n "$BIN_HOMEBREW" ]] ; then
		unset HOMEBREW_SHELLENV_PREFIX # dirty hack
		eval $($BIN_HOMEBREW shellenv)
		
		# Set up common library flags for compilation
		for libname in readline zlib openssl@3 portaudio; do
			if [[ -d "$($BIN_HOMEBREW --prefix $libname 2>/dev/null)" ]]; then
				export LDFLAGS="-L$($BIN_HOMEBREW --prefix $libname)/lib $LDFLAGS"
				export CFLAGS="-I$($BIN_HOMEBREW --prefix $libname)/include $CFLAGS"
			fi
		done
	fi
	
	# Set up Xcode SDK path
	if [[ -x /usr/bin/xcrun ]]; then
		export SDKPATH=`xcrun --show-sdk-path`/usr/include
	fi
	
	# Set up pkg-config path
	if [[ -d "/usr/local/opt/libxml2/lib/pkgconfig" || -d "/usr/local/opt/zlib/lib/pkgconfig" ]]; then
		export PKG_CONFIG_PATH="/usr/local/opt/libxml2/lib/pkgconfig:/usr/local/opt/zlib/lib/pkgconfig"
	fi

	# Set Android SDK path if it exists
	[[ -d "$HOME/Library/Android/sdk" ]] && export ANDROID_SDK=$HOME/Library/Android/sdk

	# macOS specific aliases
	alias locate='mdfind -name'
	alias :sleep="pmset sleepnow"
	alias GetInProgress="mdfind 'kMDItemUserTags==InProgress'"
	alias SetInProgress="xattr -w com.apple.metadata:_kMDItemUserTags 'InProgress' "
	alias GetDeletable="mdfind 'kMDItemUserTags==Deletable'"
	alias SetDeletable="xattr -w com.apple.metadata:_kMDItemUserTags 'Deletable' "
	abbrev-alias sayen="say -v 'Ava (Premium)'"
	abbrev-alias sayuk="say -v Daniel"
	abbrev-alias sayjp="say -v 'Kyoko (Enhanced)'"
	abbrev-alias saych="say -v Tingting"
	alias QuickLook="qlmanage -p"
	alias :TimeMachineLog="log stream --style syslog --predicate 'senderImagePath contains[cd] \"TimeMachine\"' --info"
	alias HeySiri="open -a Siri"
	alias objdump="objdump --x86-asm-syntax=intel"
	alias zsh_on_rosetta="arch -x86_64 /bin/zsh"
	abbrev-alias gdb="arch -x86_64 gdb -q -ex 'set disassembly-flavor intel' -ex 'disp/i \$pc'"

	# Use MacVim's CLI version if available
	if [ -x "/usr/local/bin/mvim" ]; then
		alias vim="/usr/local/bin/mvim -v"
	fi
	
	# Add CotEditor to path if available
	if [ -x "/Applications/CotEditor.app/Contents/SharedSupport/bin/cot" ]; then
		alias cot="/Applications/CotEditor.app/Contents/SharedSupport/bin/cot"
	fi
	
	# Set up Google Cloud SDK if available
	if [ -d "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/" ]; then
		source "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc"
		source "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/completion.zsh.inc"
	fi
	end_of "macOS specific settings"
fi

alias :tailf_syslog='sudo tail -f /var/log/syslog | ccze'
alias :tailf_message='sudo tail -f /var/log/messages | ccze'
if [ -e /var/log/apache2/access_log ] ; then
	alias :tailf_apacheaccesslog='sudo tail -f /var/log/apache2/access_log | ccze'
	alias :tailf_apacheerrorlog='sudo tail -f /var/log/apache2/error_log | ccze'
	alias :tailf_apachelog='sudo tail -f /var/log/apache2/error_log /var/log/apache2/access_log | ccze'
else
	alias :tailf_apacheaccesslog='sudo tail -f /var/log/apache2/access.log | ccze'
	alias :tailf_apacheerrorlog='sudo tail -f /var/log/apache2/error.log | ccze'
	alias :tailf_apachelog='sudo tail -f /var/log/apache2/error.log /var/log/apache2/access.log | ccze'
fi


# ----- Hooks
function :title(){

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
		cd|__enhancd::cd)
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
	:title $Title

}
local COMMAND=""
local COMMAND_TIME="0"
function CheckCommandTime_preexec(){

	# --- notify long command
	COMMAND="$1"
	COMMAND_TIME=`date +%s`	# start time (Unix epoch)

}
function CheckCommandTime_precmd(){

	# --- notify long command
	IsError=$?
	if [[ "$COMMAND_TIME" -ne "0" ]]; then
		local d=`date +%s`
		d=`expr $d - $COMMAND_TIME`
		# if the command takes more than 30 seconds, notify with terminal
		if [[ "$d" -ge "30" ]] ; then
			# if the command takes more than 30 minutes, notify with slack

			# ignore zsh, tmux, ssh, mosh
			if [[ "$COMMAND" =~ ^(zsh|tmux|ssh|mosh) ]]; then
				return
			fi

			# set COMMAND_INFO to
			#  $COMMAND without double quotes
			#  First 20 character
			local COMMAND_INFO=`echo $COMMAND | sed -e 's/^"//' -e 's/"$//' | cut -c 1-20`
			if [[ IsError -ne 0 ]]; then
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
end_of "hooks"

if [[ $OSTYPE = *darwin* ]] ; then
	if [ -f $($BIN_HOMEBREW --prefix)/opt/asdf/libexec/asdf.sh ]; then
		source $($BIN_HOMEBREW --prefix)/opt/asdf/libexec/asdf.sh
		export RUBY_CONFIGURE_OPTS="--with-openssl-dir=$($BIN_HOMEBREW --prefix openssl@1.1)"
	fi
fi

# Set up Perl paths if they exist
[[ -d "$HOME/perl5/lib/perl5" ]] && export PERL5LIB=~/perl5/lib/perl5

# Use difft for git diff if available
if [ -x /opt/homebrew/bin/difft ]; then
	export GIT_EXTERNAL_DIFF=/opt/homebrew/bin/difft
fi

# Set JAVA_HOME if zulu-17 is installed
if [ -d /Library/Java/JavaVirtualMachines/zulu-17.jdk/Contents/Home ]; then
	export JAVA_HOME=/Library/Java/JavaVirtualMachines/zulu-17.jdk/Contents/Home
fi

# --- Rust
alias cargo\ test="nocorrect cargo test"


if [ -x "`which gh`" ]; then
	# eval "$(gh copilot alias -- zsh)"
	alias "??"="gh copilot suggest -t shell"
fi
end_of "dev settings"

if [[ -x `which tmux` ]]; then
	if [[ `expr $TERM : screen` -eq 0 ]]; then
		tmux ls
	fi
elif [[ -x `which screen` ]]; then
	if [[ `expr $TERM : screen` -eq 0 ]]; then
		# sleep 1
		screen -r
	fi
else
	echo "screen not found."
fi
end_of "tmux/screen"

if [ ! -f ~/zshrc.zwc -o ~/.zshrc -nt ~/.zshrc.zwc ]; then
	# compile if modified
    zcompile ~/.zshrc
fi
end_of "zcompile"

# finally, execute fortune.
if [[ -x `which fortune` ]]; then
	echo ""
	STARTUP_FORTUNE=`fortune`
	echo -n "[$color[$hostcolor]m"
	echo $STARTUP_FORTUNE
	if [[ -x `which ollama` ]]; then
		echo -n "[2;97m"
		echo "Run [4mwhat_is_this_fortune[24m to know the meaning of this fortune."
		echo -n "[0m"
		echo ""
		function what_is_this_fortune(){
			ollama run gemma3:4b-it-qat "下記の文章を日本語で解説してください。\n$STARTUP_FORTUNE"
		}
	fi
	end_of "fortune"
fi

if (which zprof > /dev/null 2>&1); then
	zprof
fi
