#
# 700-aliases.zsh
#   Core editor and basic utility aliases
#

# ============================================================================
# Editor Aliases
# ============================================================================

abbrev-alias vi='vim -p'
abbrev-alias vimtree='vim -c "let g:nerdtree_tabs_open_on_console_startup = 1"'
abbrev-alias gvimtree='gvim -c "let g:nerdtree_tabs_open_on_console_startup = 1"'
abbrev-alias vimrc='vim ~/.vimrc'
abbrev-alias zshrc='vim ~/.zshrc'

function vimman() {
	vim -c "Man $1" -c "only"
}
abbrev-alias man='vimman'

# ============================================================================
# Core Utilities
# ============================================================================

abbrev-alias mv='nocorrect mv'
abbrev-alias cp='nocorrect cp'
abbrev-alias mkdir='nocorrect mkdir'
abbrev-alias su='su -s =zsh'
abbrev-alias pv='pv -pterabT -i 0.3 -c -N Progress'
abbrev-alias od='od -Ax -tx1 -c'
abbrev-alias hexdump='hexdump -C'
abbrev-alias hex2bin='xxd -r -p'

# Platform-specific ls aliases
if [[ "$OSTYPE" = darwin* || "$OSTYPE" = freebs* ]]; then
	alias ls='ls -FG'
	alias la='ls -FG -a'
	alias ll='ls -FG -la -t -r -h'
else
	alias ls='ls -F --color=auto'
	alias la='ls -F -a --color=auto'
	alias ll='ls -F -la -t -r --human-readable --color=auto'
fi

# Disk utilities
abbrev-alias du='du -hcs *'
abbrev-alias df='df -H'

# ============================================================================
# Pagers
# ============================================================================

if [[ -f /usr/share/vim/vimcurrent/macros/less.sh ]]; then
	alias less=/usr/share/vim/vimcurrent/macros/less.sh
else
	# Find the first vim less.sh script and use it
	_aliases_vim_less=$(command find /usr/share/vim -name 'less.sh' -type f 2>/dev/null | head -n1)
	if [[ -n "$_aliases_vim_less" && -f "$_aliases_vim_less" ]]; then
		alias less=$_aliases_vim_less
	else
		alias less='less --ignore-case --status-column --prompt="?f%f:(stdin).?m(%i/%m files?x, next %x.). ?c<-%c-> .?e(END):%lt-%lb./%Llines" --hilite-unread --tabs=4 --window=-5'
	fi
	unset _aliases_vim_less
fi

# ============================================================================
# Network & Web
# ============================================================================

abbrev-alias w3m='noglob _w3m'
abbrev-alias wget='noglob wget'
abbrev-alias wget-recursive='noglob wget -r -l5 --convert-links --random-wait --restrict-file-names=windows --adjust-extension --no-parent --page-requisites --quiet --show-progress -e robots=off'
abbrev-alias youtube-dl='noglob yt-dlp'
abbrev-alias ping='ping -a -c4'
abbrev-alias ping6='ping6 -a -c4'
abbrev-alias monitor_network='sudo trip --geoip-mmdb-file ~/GeoLite2-City.mmdb --tui-geoip-mode short profile.kcrt.net 8.8.8.8'
abbrev-alias serve_http_here='python3 -m http.server'

# ============================================================================
# Zsh Utilities
# ============================================================================

alias zmv='noglob zmv'
alias zcp='noglob zmv -C'
alias zln='noglob zmv -L'