#
#	400-prompt.zsh
#		Title bar, VCS info, and prompt configuration
#


# ----- Version Control (svn, git) branch display
autoload -Uz vcs_info
autoload -Uz add-zsh-hook
# formats: Normal state, actionformats: Special states like merge conflict
# %s -> VCS in use, %b -> branch, %a -> action
zstyle ':vcs_info:*' formats '%s: %b%c%u'
zstyle ':vcs_info:*' actionformats '%s: %b%c%u[%a]'
zstyle ':vcs_info:git:*' check-for-changes true
zstyle ':vcs_info:git:*' stagedstr "📌"
zstyle ':vcs_info:git:*' unstagedstr "📝"
precmd_vcs_info () {
	psvar=()
	LANG=en_US.UTF-8 vcs_info
	[[ -n "$vcs_info_msg_0_" ]] && psvar[1]="$vcs_info_msg_0_"
}
add-zsh-hook precmd precmd_vcs_info
RPROMPT="%1(v|%F{green}%1v%f|)"

# ----- Prompt configuration
if [[ $UID -eq 0 ]]; then
	PROMPT_COLOR="%F{red}"
else
	PROMPT_COLOR="%F{$hostcolor}"
fi

# Calculate shell level (adjust for terminal multiplexers)
adjust_shell_level() {
	local level=$SHLVL
	case "$TERM_PROGRAM" in
		vscode)		level=$((level - 3)) ;;
	esac
	if [[ -n "$TMUX" || -n "$ZELLIJ" ]]; then
		level=$((level - 1))
	fi
	echo $level
}

SUBSTLV=$(adjust_shell_level)
if [[ $SUBSTLV -gt 1 ]]; then
	PROMPT_SUBSTLV="${(l:$((SUBSTLV - 1))::>:)}"
	PROMPT_SUBSTLV="%B${PROMPT_SUBSTLV}%b"
else
	PROMPT_SUBSTLV=""
fi

PROMPT_USER='%n'
PROMPT_HOST='${${${(%):-%M}%%.local}%.kcrtjp.internal}'
PROMPT_MAILCHECK=$([[ -x ${DOTFILES}/script/have_mail.sh ]] && echo '$(~/dotfiles/script/have_mail.sh)' || echo '')
PROMPT_SHARP='%# '
PROMPT_RESETCOLOR='%{$reset_color%}'
PROMPT="${PROMPT_SUBSTLV}${PROMPT_COLOR}[${PROMPT_USER}@${PROMPT_HOST}]${PROMPT_MAILCHECK}${PROMPT_SHARP}${PROMPT_RESETCOLOR}"

# Right prompt: inverts on last command error
RPROMPT_BGJOB='%(1j.(bg: %j).)'
RPROMPT_SETCOLOR=' %{%(?.$fg[cyan].$bg[cyan]$fg[black])%}'
RPROMPT_DIR=' [%(5~|%-2~/.../%2~|%~)] '
RPROMPT_PLATFORM='($(uname -m)) '
PROMPT_TIME='%F{8}%D{%H:%M:%S}%f '
RPROMPT="${RPROMPT}${RPROMPT_BGJOB}${RPROMPT_SETCOLOR}${RPROMPT_DIR}${RPROMPT_PLATFORM}${PROMPT_TIME}${PROMPT_RESETCOLOR}"
