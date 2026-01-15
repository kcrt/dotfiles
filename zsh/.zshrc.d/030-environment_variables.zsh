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
