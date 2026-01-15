#
# 705-aliases-convenience.zsh
#   Convenience aliases, special commands, and dynamic aliases
#

# ============================================================================
# Abbreviations
# ============================================================================

abbrev-alias hist='history'
abbrev-alias mutt='neomutt'

# ============================================================================
# Directory Navigation
# ============================================================================

alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'

# Japanese directories
alias 医療='cd ~/Documents/医療'
alias 研究='cd ~/Documents/医療/研究'
alias 依頼='cd ~/Documents/医療/依頼'

# ============================================================================
# System Utilities
# ============================================================================

alias cls='clear'
alias beep='print "\a"'
alias pstree='pstree -p'
alias history='history -E 1'
alias sudo='sudo -E '  # Trailing space allows alias expansion (e.g., sudo ll)

# ============================================================================
# Quit Function
# ============================================================================

# Exits virtual environment if active, otherwise exits shell
function quit_command() {
	if [[ -n "$VIRTUAL_ENV" ]]; then
		deactivate
	else
		exit
	fi
}
alias :q='quit_command'

# ============================================================================
# Special Commands
# ============================================================================

# Comic archive management
abbrev-alias eee='noglob zmv -v "([a-e|s|g|x])(*\(*\) \[*\]*).zip" "/Volumes/eee/comics/\${(U)1}/\$2.zip"'

# One-liner utilities
abbrev-alias :svnsetkeyword='svn propset svn:keywords "Id LastChangeDate LastChangeRevision LastChangeBy HeadURL Rev Date Author"'
abbrev-alias :checkjpeg='find . -name "*.jpg" -or -name "*.JPG" -exec jpeginfo -c {} \;'
abbrev-alias :howmanyfiles='find . -print | wc -l'

# ============================================================================
# Global Aliases
# ============================================================================

alias -g N='; OSNotify "shell" "operation finished"'

# ============================================================================
# Dynamic Aliases (from dotfiles directories)
# ============================================================================

# Sheet files (cheatsheets)
for f in $(find "${DOTFILES}/sheet" -maxdepth 1 -mindepth 1 -type f); do
	if [[ ${f:e} == "md" ]] && command -v glow &> /dev/null; then
		alias ":howto${f:t:r}"="glow -p $f"
	else
		alias ":howto${f:t:r}"="cat $f"
	fi
done

# Scripts folder
for f in "${DOTFILES}"/script/*; do
	alias "${f:t:r}"="$f"
done

# ============================================================================
# Utility One-Liners
# ============================================================================

abbrev-alias dirsizeinbyte="find . -type f -print -exec wc -c {} \; | awk '{ sum += \$1; }; END { print sum }'"
abbrev-alias finddups="find * -type f -exec shasum \{\} \; | sort | tee /tmp/shasumlist | cut -d' ' -f 1 | uniq -d > /tmp/duplist; while read DUPID; do grep \$DUPID /tmp/shasumlist; done < /tmp/duplist"
abbrev-alias iconv-nfdtonfc="iconv -f UTF-8-MAC -t UTF-8"
abbrev-alias iconv-nfctonfd="iconv -f UTF-8 -t UTF-8-MAC"
abbrev-alias verynice="nice -n 20 "

# ============================================================================
# Root-specific Settings
# ============================================================================

if [[ $USER != 'root' ]]; then
	alias updatedb='sudo updatedb; beep'
fi

# ============================================================================
# Log Viewing
# ============================================================================

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

# ============================================================================
# SSH and Remote Code
# ============================================================================

# `code_<hostname> <path>` to run `code --remote ssh-remote+<hostname> <path>`
# Also creates ls_<hostname>, ll_<hostname>, la_<hostname> aliases
# Analyze ~/.ssh/config to get the hostname
if [[ -f ~/.ssh/config ]]; then
	grep -E '^Host ' ~/.ssh/config | awk '{print $2}' | while read -r host; do
		# assert it is valid host name [a-zA-Z0-9_.-]
		if [[ ! $host =~ ^[a-zA-Z0-9_.-]+$ ]]; then
			continue
		fi
		eval "alias code_$host=\"code --remote ssh-remote+$host\""
		eval "alias ls_$host=\"ssh $host ls\""
		eval "alias ll_$host=\"ssh $host ls -l \""
		eval "alias la_$host=\"ssh $host ls -a \""
	done
fi
