#
#	020-options.zsh
#		Zsh options and history settings
#

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
stty stop undef						# ^Sとかを無効にする (terminal level)
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
