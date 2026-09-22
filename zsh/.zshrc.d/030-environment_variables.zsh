#
#	030-environment_variables.zsh
#		Core environment variables
#

# ----- 環境変数
export LANG=ja_JP.UTF-8
export EDITOR="vim"
export COLOR="tty"
export PYTHONSTARTUP=${DOTFILES}/pythonrc.py
export GOOGLE_APPLICATION_CREDENTIALS="`echo ~/secrets/kcrtjp-google-serviceaccount.json`"
# rg は既定の設定ファイル位置を持たないので明示的に指す (stow package: ripgrep)
export RIPGREP_CONFIG_PATH="$HOME/.config/ripgrep/config"

# ----- restic
# 手で restic backup を打ったとき用。これが無いと $HOST の実値が記録されるが、
# macOS は mDNS 次第で aluminum / aluminum.local を返し分ける。restic は親
# スナップショットを (host, paths) で探すので、綴りが違うだけで親を見失って
# 全ファイルを読み直し、forget --group-by host,paths も別系統として扱ってしまう。
# restic_backup.sh は --host を明示するので無関係だが、手打ちは無防備なのでここで塞ぐ。
# $HOST は zsh 組み込みなので hostname を fork しない。
export RESTIC_HOST="${HOST%.local}"

# repo と鍵は、カードが刺さっているときだけ。この dotfiles は Codespaces にも
# 配られるので (.zshenv 参照)、無条件に /Volumes/... を指すと嘘になる。
# restic は cwd を repo とみなすフォールバックを持たないため、未設定なら
# "Please specify repository location" で止まるだけで、誤爆はしない。
# -r を明示すればこの既定より常に優先される。
if [[ -d "/Volumes/microSD/backup/restic-repo" ]]; then
	export RESTIC_REPOSITORY="/Volumes/microSD/backup/restic-repo"
	export RESTIC_PASSWORD_FILE="$HOME/.config/restic/password"
fi
