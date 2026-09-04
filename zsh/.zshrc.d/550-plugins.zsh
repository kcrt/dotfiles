#
#	070-plugins.zsh
#		Sheldon, zoxide, and plugin configuration
#

# `abbrev-alias` は zsh-abbrev-alias プラグインが提供するが、後続の
# 655/700 系ファイルが無条件に呼び出す。プラグインが読み込まれない場合
# (Claude Code 内、または sheldon 未インストール) でもエラーを出さないよう、
# 先に何もしないスタブを定義しておく (プラグイン読み込み時に上書きされる)。
function abbrev-alias(){
	# skip this command
}

# Skip all plugin loading when in Claude Code
[[ -n "$CLAUDECODE" ]] && return 0

# ----- sheldon (plugin manager)
if command -v sheldon &> /dev/null; then
	eval "$(sheldon source)"
else
	echo_warn "Please install sheldon for zsh plugins: https://sheldon.cli.rs/Installation.html"
	if [[ "$OSTYPE" = darwin* ]]; then
		echo_warn "  macOS: brew install sheldon"
	elif command -v cargo &> /dev/null; then
		echo_warn "  Linux: cargo binstall sheldon  (or: cargo install sheldon)"
	else
		echo_warn "  Linux: install rustup first, then 'cargo binstall sheldon':"
		echo_warn "    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
	fi
	# abbrev-alias はファイル冒頭のスタブがそのまま使われる
fi

# ----- zoxide (smarter cd command)
if command -v zoxide &> /dev/null; then
	# --cmd cd: make zoxide override cd command (same as `alias cd='zoxide`, but better`)
	# ただし古い zoxide (~v0.5, apt などで入るもの) が生成する内部関数は
	# `builtin cd` ではなく `cd` を呼ぶため、--cmd cd と併用すると
	# cd -> _z_cd -> cd ... と無限再帰し
	# `cd:1: maximum nested function level reached` で cd が全く使えなくなる。
	# 生成コードが builtin cd を使っているかどうかで判定する。
	_zoxide_init="$(zoxide init zsh --cmd cd 2>/dev/null)"
	if [[ "$_zoxide_init" == *"builtin cd"* ]]; then
		eval "$_zoxide_init"
	else
		# cd は builtin のまま残し、z / zi だけを有効にする
		[[ "$(whence -w cd)" == "cd: function" ]] && unfunction cd
		eval "$(zoxide init zsh)"
		echo_warn "Warning: zoxide $(zoxide --version 2>/dev/null | awk '{print $2}') is too old to replace 'cd' (use 'z' instead)."
	fi
	unset _zoxide_init
else
	echo_warn "Warning: zoxide is not installed."
	if [[ "$OSTYPE" = darwin* ]]; then
		echo_warn "  macOS: brew install zoxide"
	else
		echo_warn "  Debian 12+: sudo apt install zoxide  (older apt versions are too old for 'cd' integration)"
		echo_warn "  Other Linux: curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh"
	fi
fi

# ----- direnv (directory-based environment variables)
if command -v direnv &> /dev/null; then
	eval "$(direnv hook zsh)"
else
	echo_warn "Warning: direnv is not installed."
	if [[ "$OSTYPE" = darwin* ]]; then
		echo_warn "  macOS: brew install direnv"
	else
		echo_warn "  Ubuntu/Debian: sudo apt install direnv"
		echo_warn "  Other Linux: curl -sfL https://direnv.net/install.sh | bash"
	fi
fi

# ----- Bracketed paste
# Enable bracketed paste magic for URL handling
# (prevent http://www.kcrt.net?q=hello try to match local files
autoload -Uz bracketed-paste-url-magic
zle -N bracketed-paste bracketed-paste-url-magic

# ----- zsh-syntax-highlighting configuration
ZSH_HIGHLIGHT_HIGHLIGHTERS=(main brackets pattern cursor)
