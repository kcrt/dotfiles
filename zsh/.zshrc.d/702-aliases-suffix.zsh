#
# 702-aliases-suffix.zsh
#   Suffix aliases for automatic file handling
#

# ============================================================================
# Text Files
# ============================================================================

alias -s txt='less'
alias -s log='tail -f -n20'
alias -s html='w3m'
alias -s json='jq -C .'
alias -s asc='vim'

# ============================================================================
# Images
# ============================================================================

alias -s png='img2sixel'
alias -s jpg='img2sixel'

# ============================================================================
# Archives
# ============================================================================

alias -s zst='~/dotfiles/script/tar-zstd-expand.sh'

# ============================================================================
# Markdown (glow > bat > cat)
# ============================================================================

if command -v glow &> /dev/null; then
	alias -s md='glow -p'
elif command -v bat &> /dev/null; then
	alias -s md='bat --paging=always --color=always'
else
	alias -s md='cat'
fi

# ============================================================================
# DOCX (doxx > custom script)
# ============================================================================

if command -v doxx &> /dev/null; then
	alias -s docx='doxx --images --color'
else
	alias -s docx='~/dotfiles/script/tomd_and_show.sh'
fi

# ============================================================================
# Spreadsheets (xleak)
# ============================================================================

if command -v xleak &> /dev/null; then
	alias -s xlsx='xleak -i'
	alias -s xls='xleak -i'
	alias -s odt='xleak -i'
fi

# ============================================================================
# R and RMarkdown
# ============================================================================

if command -v Rscript &> /dev/null; then
	alias -s R='Rscript'
	function render_rmarkdown_and_open() {
		Rscript -e "rmarkdown::render('$1')"
		open "${1:r}.html"
	}
	alias -s Rmd='render_rmarkdown_and_open'
fi
