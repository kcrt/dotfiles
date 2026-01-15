# ==============================================================================
# 300-completion.zsh
#   補完オプション・設定・初期化
# ==============================================================================

# ------------------------------------------------------------------------------
# 基本的な補完オプション
# ------------------------------------------------------------------------------
LISTMAX=200                          # 表示する最大補完リスト数
setopt auto_list                     # 曖昧な補完で自動的にリスト表示
setopt NO_menu_complete              # 一回目の補完で候補を挿入(cf. auto_menu)
setopt auto_menu                     # 二回目の補完で候補を挿入
setopt magic_equal_subst             # --include=/usr/... などの=補完を有効に
setopt NO_complete_in_word           # カーソル位置で補完する
setopt list_packed                   # 補完候補をできるだけつめて表示する
setopt NO_list_beep                  # 補完候補表示時にビープ音を鳴らさない
setopt list_types                    # ファイル名の末尾に識別マークをつける
setopt INTERACTIVE_COMMENTS          # インタラクティブモードでもコメントを許可

# ------------------------------------------------------------------------------
# 補完スタイル設定
# ------------------------------------------------------------------------------
zstyle ':completion:*' format '%B%d%b'
zstyle ':completion:*' group-name ''                      # 補完候補をグループ化する
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}    # 補完も色づけ
zstyle ':completion:*' use-cache yes
zstyle ':completion:*' cache-path "${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zcompcache"
zstyle ':completion:*' completer _expand _complete _ignored _approximate
zstyle ':completion:*' matcher-list '' 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=*' 'l:|=* r:|=*'
zstyle ':completion:*' verbose yes                        # 詳細な情報を使う
zstyle ':completion:*' menu select=2                      # メニュー選択を有効化
zstyle ':completion:sudo:*' environ PATH="$SUDO_PATH:$PATH" # sudo時にsudo用のパスも使う

# プロセス補完のスタイル
zstyle ':completion:*:processes' command 'ps x -o pid,args'  # kill <tab>での補完
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#) ([0-9a-z-]#)*=01;34=0=01'

# ------------------------------------------------------------------------------
# Rust/Cargo 補完（キャッシュ付き）
# ------------------------------------------------------------------------------
if [[ -d "$HOME/.cargo" && -x "$HOME/.cargo/bin/rustc" ]]; then
	# キャッシュ設定
	CARGO_COMPLETION_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/cargo-completion"
	CARGO_COMPLETION_DIR=""
	mkdir -p "$(dirname "$CARGO_COMPLETION_CACHE" 2>/dev/null)"

	# キャッシュを更新または読み込み（7日ごとに更新）
	if is_file_older_than_days "$CARGO_COMPLETION_CACHE" 7; then
		CARGO_COMPLETION_DIR="$($HOME/.cargo/bin/rustc --print sysroot 2>/dev/null)/share/zsh/site-functions"
		echo "$CARGO_COMPLETION_DIR" > "$CARGO_COMPLETION_CACHE"
	else
		CARGO_COMPLETION_DIR=$(cat "$CARGO_COMPLETION_CACHE" 2>/dev/null)
	fi

	# 補完ディレクトリをFPATHに追加
	if [[ -n "$CARGO_COMPLETION_DIR" && -d "$CARGO_COMPLETION_DIR" ]]; then
		FPATH="$CARGO_COMPLETION_DIR:${FPATH}"
	fi
fi

# ------------------------------------------------------------------------------
# 補完初期化
# ------------------------------------------------------------------------------
# rootユーザーはスキップ
if [[ $UID -ne 0 ]]; then
	autoload -Uz compinit

	# 補完ダンプファイルのパスを設定
	if [[ -z "$ZSH_COMPDUMP" ]]; then
		ZSH_COMPDUMP="${ZDOTDIR:-$HOME}/.zcompdump-zsh${ZSH_VERSION}"
	fi

	# 再生成が必要かチェック（1日1回）
	if is_file_older_than_days "$ZSH_COMPDUMP" 1; then
		compinit -d "$ZSH_COMPDUMP"           # 完全再生成（セキュリティチェック含む）
	else
		compinit -C -d "$ZSH_COMPDUMP"         # 高速読み込み（セキュリティチェックをスキップ）
	fi
fi
