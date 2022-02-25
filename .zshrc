
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

source ${DOTFILES}/script/OSNotify.sh
source ${DOTFILES}/script/echo_color.sh
source ${DOTFILES}/script/miscs.sh
source ${DOTFILES}/no_git/secrets.sh

# ----- 環境変数
export LANG=ja_JP.UTF-8
export EDITOR="vim"				# やっぱりvimだね
export COLOR="tty"
export GPG_TTY=$(tty)
export PYTHONSTARTUP=${DOTFILES}/pythonrc.py
export GOOGLE_APPLICATION_CREDENTIALS="`echo ~/secrets/kcrtjp-google-serviceaccount.json`"
stty stop undef					# ^Sとかを無効にする

# ----- ホスト毎にプロンプト色の変更
typeset -A hostcolors
typeset -A hostblacks
hostcolors=(kcrt.net cyan rctstudy.jp cyan nitrogen.local blue oxygen.local blue neon yellow lithium yellow aluminum.local blue)
hostblacks=(kcrt.net 001111 rctstudy.jp 001111 nitrogen.local 000011 oxygen.local 000011 neon 001111 lithium 001111 aluminum.local 000011)
if [[ "$hostcolors[$HOST]" == "" ]]; then
	hostcolor=magenda
	hostblack="000000"
else
	hostcolor=$hostcolors[$HOST]
	hostblack=$hostblacks[$HOST]
fi
if [[ "$TERM" == (screen*|xterm*) && "$SSH_CONNECTION" == "" ]]; then
	echo -n "]R"				# first, reset the palette
	echo -n "]P0$hostblack"	# black
	echo -n "]P1FF0000"		# red
	echo -n "]P200CC00"		# green
	echo -n "]P3CCCC00"		# yellow
	echo -n "]P45555FF"		# blue
	echo -n "]P5FF00FF"		# magenta
	echo -n "]P600FFFF"		# cyan
	echo -n "]P7CCCCCC"		# white
	echo -n "]P8888888"		# BLACK
	echo -n "]P9FFAAAA"		# RED
	echo -n "]PA88FF88"		# GREEN
	echo -n "]PBFFFFAA"		# YELLOW
	echo -n "]PC7777FF"		# BLUE
	echo -n "]PDFFCCFF"		# MAGENTA
	echo -n "]PE88FFFF"		# CYAN
	echo -n "]PFFFFFFF"		# WHITE
fi

# ----- タイトルバーの文字列
if [[ "$SSH_CONNECTION" != "" ]]; then
	# ssh接続
	local title="`echo -n $SSH_CONNECTION | sed -e 's/\(.*\) .* \(.*\) .*/\1 --> \2/g'`"
	echo "]2;$HOST($title, ssh)\a"
elif [[ "$REMOTEHOST" != "" ]]; then
	# おそらくtelnet
	echo -n "]2;$REMOTEHOST --> $HOST\a";
elif [[ "$OSTYPE" == "cygwin" ]]; then
	# cygwin
	echo -n "]2;$HOST (cygwin)\a";
else
	# 普通のローカル
	echo -n "]2;$HOST (local)\a"
fi

# ----- 色関係
autoload colors					# $color[red]とかが使えるようになる。
colors
if [[ -x dircolors ]]; then
	eval `dircolors -b`
fi
export ZLS_COLORS=$LS_COLORS
export CLICOLOR=true

# ----- autoloadたち
autoload -Uz is-at-least		# versionによる判定
autoload -U compinit
compinit -u
autoload zmv
autoload zargs
autoload zsh/files
autoload -Uz url-quote-magic
if [[ -f /etc/zsh_command_not_found ]]; then
	source /etc/zsh_command_not_found
fi


# ----- 補完
LISTMAX=200							# 表示する最大補完リスト数
setopt auto_list					# 曖昧な補完で自動的にリスト表示
setopt NO_menu_complete				# 一回目の補完で候補を挿入(cf. auto_menu)
setopt auto_menu					# 二回目の補完で候補を挿入
setopt magic_equal_subst			# --include=/usr/... などの=補完を有効に
setopt NO_complete_in_word			# TODO:よくわからない
setopt list_packed					# 補完候補をできるだけつめて表示する
setopt NO_list_beep					# 補完候補表示時にビープ音を鳴らす
setopt list_types					# ファイル名のおしりに識別マークをつける
zstyle ':completion:*' format '%B%d%b'
zstyle ':completion:*' group-name ''	# 補完候補をグループ化する
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}	# 補完も色つける
zstyle ':completion:*' use-cache yes
zstyle ':completion:*' completer _complete _approximate
zstyle ':completion:*' verbose yes 	# 詳細な情報を使う。
zstyle ':completion:sudo:*' environ PATH="$SUDO_PATH:$PATH" # sudo時にはsudo用のパスも使う。
zstyle ':completion:*:default' menu select=2
zstyle ':completion:*:processes' command 'ps x -o pid,args'	# kill <tab>での補完


# ----- 履歴
HISTFILE="$HOME/.zhistory"			# 履歴保存先
HISTSIZE=100000						# 使用する履歴数
SAVEHIST=100000						# 保存する履歴数
setopt hist_ignore_space			# スペースで始まるコマンドを記録しない
setopt hist_ignore_all_dups			# 重複した履歴を記録しない
setopt share_history				# ターミナル間の履歴を共有する
setopt append_history				# 履歴を追記する

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

# ----- プロンプト
PROMPT='%{%(!.$fg[red].$fg[$hostcolor])%}[%n@%m] %# %{$reset_color%}'
# 最後に実行したプログラムがエラーだと反転するよ。
RPROMPT="$RPROMPT %{%(?.$fg[cyan].$bg[cyan]$fg[black])%} [%~] ($(uname -m)) %{$reset_color%}"

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

# ----- 自分用関数
function ShowStatus(){

	# モードの切り替え時に右上にモードを表示
	integer Cursor_X
	integer Cursor_Y
	integer StrLength
	StrLength=$(echo -n $1 | wc -m)
	Cursor_X=$[COLUMNS-$StrLength]	# 場所はお好みで
	Cursor_Y=1
	echo -n "[s"			# push pos
	echo -n "[$[$Cursor_Y];$[$Cursor_X]H"	# set pos
	echo -n "[07;37m$1[m" # print
	echo -n "[u"			# pop pos

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


# ----- パス
export PATH=~/.deno/bin:$PATH:$GOPATH/bin:~/.cargo/bin

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
function :svnwhatsnew(){
	vimdiff =(svn cat --revision PREV $1) =(svn cat --revision HEAD $1)
}
fucntion :svnwhatchanged(){
	vimdiff $1 =(svn cat --revision HEAD $1)
}
function trash(){

    if [ $# = 0 ]; then
		command rm
        return 1
    fi

    if [ ! -d ~/.trash ]; then
        echo "ERROR : ~/.trash not found!"
        return 1
    fi

    mv $@ ~/.trash || return

    if [ $# = 1 ]; then
        echo "'$1' was moved into trash!"
    else
        echo "$# files were moved into trash!"
    fi

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

# ----- エイリアス
# コマンド置き換え
alias vi='vim -p'
alias vimtree='vim -c "let g:nerdtree_tabs_open_on_console_startup = 1"'
alias gvimtree='gvim -c "let g:nerdtree_tabs_open_on_console_startup = 1"'
alias vimrc='vim ~/.vimrc'
alias zshrc='vim ~/.zshrc'
alias rm='trash'
alias mv='nocorrect mv'
alias cp='nocorrect cp'
alias mkdir='nocorrect mkdir'
alias w3m=' noglob _w3m'
alias exstrings='${DOTFILES}/script/exstrings.sh'
alias gdb="gdb -q -ex 'set disassembly-flavor intel' -ex 'disp/i \$pc'"
alias mutt='neomutt'
if [[ -x `which thefuck` ]]; then
	eval "$(thefuck --alias)"
fi
alias ssh-sign="ssh-keygen -Y sign -f ~/.ssh/kcrt-ssh-ed25519.pem -n file"
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
alias du='du -hcs *'
alias df='df -H'
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
alias wget='noglob wget'
alias ping='ping -a -c4'
alias sudo='sudo -E '	#スペースを付けておくとsudo llなどが使える
alias ag='ag -S'
alias grep='grep --color=auto --binary-file=without-match --exclude-dir=.git --exclude-dir=.svn'
alias dstat='sudo dstat -t -cl --top-cpu -m -d --top-io -n'
alias wget-recursive="noglob wget -r -l5 --convert-links --random-wait --restrict-file-names=windows --adjust-extension --no-parent --page-requisites --quiet --show-progress -e robots=off"
function ffmpeg_gif(){
	ffmpeg -i "$1" -an -r 15 -pix_fmt rgb24 -f gif "${1:t:r}.gif"
}
function ffmpeg_deinterlaced_mp4(){
	ffmpeg -i "$1" -vf "yadif=0:-1" -pix_fmt yuv420p "${1:t:r}.mp4"
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
function ffmpeg_1080p_h264(){
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libx264 "${1:t:r} [1080p h264].mp4"
}
function ffmpeg_1080p_hevc(){
	ffmpeg -i "$1" -vf scale=-1:1080 -c:v libx265 "${1:t:r} [1080p hevc].mp4"
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
	if [ $# -eq 0 ]; then
		echo "example: mcd iryou" 
	elif [ $# -eq 1 ]; then
		migemolist=`cmigemo -d /opt/homebrew/Cellar/cmigemo/*/share/migemo/utf-8/migemo-dict -w "$1"`
		dirname=`ls | grep --color=never -E $migemolist`
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
alias hist='history'
alias :q='exit'
alias su='su -s =zsh'
alias hexdump='od -Ax -tx1 -c'
alias hex2bin="xxd -r -p"
alias beep='print "\a"'
alias cls='clear'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
function vimman(){
	vim -c "Man $1" -c "only"
}
alias man='vimman'
alias clang++11='clang++ -O --std=c++11 -Wall --pedantic-errors --stdlib=libc++'
alias clang++14='clang++ -O --std=c++14 -Wall --pedantic-errors --stdlib=libc++'
alias clang++17='clang++ -O --std=c++17 -Wall --pedantic-errors --stdlib=libc++'
alias clang++20='clang++ -O --std=c++20 -Wall --pedantic-errors --stdlib=libc++'
alias icat='icat --mode h'
alias eee='noglob zmv -v "([a-e|s|g])(*\(*\) \[*\]*).zip" "/Volumes/eee/comics/\${(U)1}/\$2.zip"'
alias textlintjp="textlint --preset preset-japanese --rule spellcheck-tech-word --rule joyo-kanji --rule @textlint-rule/textlint-rule-no-unmatched-pair"
alias decryptpdf="gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=unencrypted.pdf -c 3000000 setvmthreshold -f"
alias pdb="`which env` python -m pdb"
alias docker_busybox="docker run -it --rm busybox"
alias docker_busybox_mount_here="docker run -it --rm -v `pwd`:/root busybox"
alias docker_alpine="docker run -it --rm alpine"
alias docker_alpine_mount_here="docker run -it --rm -v `pwd`:/root alpine"
alias docker_ubuntu="docker run -it --rm ubuntu"
alias docker_ubuntu_x86="docker run -it --platform linux/amd64 --rm ubuntu"
alias docker_ubuntu_mount_here="docker run -it --rm -v `pwd`:/root ubuntu"
alias docker_mykali="docker build --tag mykali ${DOTFILES}/docker/mykali/; docker run -it --rm --hostname='mykali' --name='mykali' -v ~/.ssh/:/home/$USER/.ssh/:ro -v ${DOTFILES}/:/home/$USER/dotfiles:ro mykali"
alias docker_myubuntu="docker build --tag myubuntu ${DOTFILES}/docker/myubuntu/; docker run -it --rm --hostname='myubuntu' --name='myubuntu' -v ~/.ssh/:/home/$USER/.ssh/:ro -v ${DOTFILES}/:/home/$USER/dotfiles:ro myubuntu"
alias wine_steam="wine64 ~/.wine/drive_c/Program\ Files\ \(x86\)/Steam/Steam.exe -no-cef-sandbox"
alias oj_test_python="oj test -c './main.py' -d tests"

# one liner
alias :svnsetkeyword='svn propset svn:keywords "Id LastChangeDate LastChangeRevision LastChangeBy HeadURL Rev Date Author"'
alias :checkjpeg='find . -name "*.jpg" -or -name "*.JPG" -exec jpeginfo -c {} \;'
alias :howmanyfiles='find . -print | wc -l'
alias serve_http_here='python3 -m http.server'
# global alias
alias -g N='; OSNotify "shell" "operation finished"'

# 思い出し用
for f in ${DOTFILES}/sheet/*; do
	if [[ -d "$f" ]]; then
		# skip
	elif [[ `cat $f | wc -l` -ge 10 ]]; then
		alias :howto${f:t}="less $f"
	else
		alias :howto${f:t}="cat $f"
	fi
done

# scriptフォルダ
for f in ${DOTFILES}/script/*; do
	alias ${f:t:r}="$f"
done

# 便利コマンド
alias dirsizeinbyte="find . -type f -print -exec wc -c {} \; | awk '{ sum += \$1; }; END { print sum }'"
alias finddups="find * -type f -exec shasum \{\} \; | sort | tee /tmp/shasumlist | cut -d' ' -f 1 | uniq -d > /tmp/duplist; while read DUPID; do grep \$DUPID /tmp/shasumlist; done < /tmp/duplist"
alias nfdtonfc="iconv -f UTF-8-MAC -t UTF-8"
alias nfctonfd="iconv -f UTF-8 -t UTF-8-MAC"
alias verynice="nice -n 20"

# ----- suffix alias (関連づけ)
alias -s exe='wine'
alias -s txt='less'
alias -s log='tail -f -n20'
alias -s html='w3m'
function viewxls(){
	w3m -T text/html =(xlhtml $1)
}
alias -s png='icat'
alias -s jpg='icat'

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
	export MANPATH=/opt/local/man:$MANPATH

	export PATH=/usr/local/opt/llvm/bin:~/Library/Android/sdk/platform-tools:$PATH
	if [[ -x /opt/homebrew/bin/brew ]] ; then
		unset HOMEBREW_SHELLENV_PREFIX # dirty hack
		eval $(/opt/homebrew/bin/brew shellenv)
	elif [[ -x /usr/local/bin/brew ]] ; then
		export HOMEBREW_CASK_OPTS="--appdir=/Applications"
		export HOMEBREW_NO_AUTO_UPDATE=1
	fi
	export LDFLAGS="-L/usr/local/opt/llvm/lib -L/usr/local/opt/zlib/lib"
	export CFLAGS="-I/usr/local/opt/llvm/include -I/usr/local/opt/zlin/include"
	export CPPFLAGS="-I/usr/local/opt/llvm/include -I/usr/local/opt/zlin/include"
	if [[ -x /usr/bin/xcrun ]]; then
		export SDKPATH=`xcrun --show-sdk-path`/usr/include
		# alias pyenv="SDKROOT=$(xcrun --show-sdk-path) pyenv"
	fi
	export PKG_CONFIG_PATH="/usr/local/opt/libxml2/lib/pkgconfig;/usr/local/opt/zlib/lib/pkgconfig"

	export ANDROID_SDK=$HOME/Library/Android/sdk

	alias locate='mdfind -name'
	alias :sleep="pmset sleepnow"
	alias GetInProgress="mdfind 'kMDItemUserTags==InProgress'"
	alias SetInProgress="xattr -w com.apple.metadata:_kMDItemUserTags 'InProgress' "
	alias GetDeletable="mdfind 'kMDItemUserTags==Deletable'"
	alias SetDeletable="xattr -w com.apple.metadata:_kMDItemUserTags 'Deletable' "
	alias sayen="say -v Alex"
	alias sayuk="say -v Daniel"
	alias sayjp="say -v Kyoko"
	alias saych="say -v Ting-Ting"
	alias QuickLook="qlmanage -p"
	alias :TimeMachineLog="log stream --style syslog --predicate 'senderImagePath contains[cd] \"TimeMachine\"' --info"
	alias HeySiri="open -a Siri"
	alias objdump="objdump --x86-asm-syntax=intel"
	alias zsh_on_rosetta="arch -x86_64 /bin/zsh"
	
	# ctags=`echo /usr/local/Cellar/ctags/*/bin/ctags`
	# alias ctags=$ctags

	if [ -x "/usr/local/bin/mvim" ]; then
		alias vim="/usr/local/bin/mvim -v"
	fi
	
	if [ -d "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/" ]; then
		source "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc"
		source "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/completion.zsh.inc"
	fi

fi

# ----- screen 使うことにしたよ
function :title(){
	# 1 : 普通の起動
	# 2 : screen上	->	TERM = "screen"
	# 3 : ssh または screen上でのssh	->	SSH_CLIENTが空でない
	# 4 : ssh上でのscreen	->	SSH_CLIENTが空でない かつ STYが空でない

	local Title=$1
	if [[ $USER == "root" ]]; then
		# rootの場合**を付ける
		Title="*$Title*"
	fi
	if [[ "$Title" == "screen" ]]; then
		# screen と表示され続けることを避ける
		Title="$HOST"
	fi

	if [[ -n $SSH_CLIENT ]]; then
		if [[ -n $STY ]]; then
			# 4 : ssh上でのscreen
			echo -n "k$Title\\"
		else
			# 3 : ssh または screen上でのssh
			# マシン名を付け加える
			if [[ $Title != "$HOST" ]]; then
				Title="$HOST:$Title"
			fi
			echo -n "]2;$Title\a"
		fi
	elif [[ "$TERM" == "screen" || "$TERM" == "screen-bce" || "$TERM" == "screen-256color" || "$TERM" == "screen-256color-bce" ]]; then
		# 2 : screen上	->	TERM = "screen"
		echo -n "k$Title\\"
	else
		# 1 : 普通の起動
		 echo -n "]2;$Title"
	fi

}

alias :split='screen -X split'
alias :only='screen -X only'
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
alias :top='screen -t top top'
alias :displays='screen -X displays'

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
		ls)
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
		ssh|ftp|telnet|mosh)
			Title="$cmd[1]:$cmd[2]";
			;;
		*)
			Title=$cmd[1];
			;;
	esac
	:title $Title

}

local COMMAND=""
local COMMAND_TIME="0"
function CheckCommandTime_preexec(){

	# --- notify long command
	COMMAND="$1"
	COMMAND_TIME=`date +%s`

}
function CheckCommandTime_precmd(){

	# --- notify long command
	IsError=$?
	if [[ "$COMMAND_TIME" -ne "0" ]]; then
		local d=`date +%s`
		d=`expr $d - $COMMAND_TIME`
		if [[ "$d" -ge "30" ]] ; then
			if [[ IsError -ne 0 ]]; then
				OSError "$COMMAND" "took $d seconds and finally failed."
			else
				OSNotify "$COMMAND" "took $d seconds and finally finished."
			fi
		fi
	fi
	COMMAND=""
	COMMAND_TIME="0"

}
add-zsh-hook preexec ShowTitle_preexec
add-zsh-hook precmd  CheckCommandTime_precmd
add-zsh-hook preexec CheckCommandTime_preexec

# ----- zplug
if [[ -r ~/.zplug/init.zsh ]]; then
	source ~/.zplug/init.zsh
	zplug "zsh-users/zsh-syntax-highlighting", defer:2
	zplug "zsh-users/zsh-history-substring-search"
	zplug "zsh-users/zsh-completions"
	zplug "plugins/brew", from:oh-my-zsh, if:"which brew"
	zplug "rupa/z", use:z.sh
	zplug "b4b4r07/enhancd", use:init.sh
	export ENHANCED_FILTER=fzy:fzf:peco
	if ! zplug check; then
		zplug check --verbose
		printf "Install? [y/N]: "
		if read -q; then
			echo; zplug install
		fi
	fi
	zplug load
else
	echo "Please execute 'curl -sL --proto-redir -all,https https://raw.githubusercontent.com/zplug/installer/master/installer.zsh| zsh' to install zplug"
fi

# ----- 開発関係
if which pyenv > /dev/null; then eval "$(pyenv init -)"; fi
export PATH="$(pyenv root)/shims:$PATH"
if which nodenv > /dev/null; then eval "$(nodenv init -)"; fi

if [[ -x `which screen` ]]; then
	if [[ `expr $TERM : screen` -eq 0 ]]; then
		# sleep 1
		screen -r
	fi
else
	echo "screen not found."
fi

if [ ! -f ~/zshrc.zwc -o ~/.zshrc -nt ~/.zshrc.zwc ]; then
	# compile if modified
    zcompile ~/.zshrc
fi

test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh"

# export NVM_DIR="$HOME/.nvm"
# [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
# [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# --- volta
# if [ -d "$HOME/.volta" ]; then
#	export VOLTA_HOME="$HOME/.volta"
#	export PATH="$VOLTA_HOME/bin:$PATH"
# fi

autoload -U +X bashcompinit && bashcompinit
complete -o nospace -C /usr/local/bin/mc mc

# finally, execute fortune.
if [[ -x `which fortune` ]]; then
	echo ""
	echo -n "[36m"
	fortune
	echo -n "[0m"
	echo ""
fi
