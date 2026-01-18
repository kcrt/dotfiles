#
#	095-development.zsh
#		Mise, Rust, Perl, Java, GitHub Copilot
#

# ===== Develop
# mise is already activated in .zshenv

# Set up Perl paths if they exist
[[ -d "$HOME/perl5/lib/perl5" ]] && export PERL5LIB=~/perl5/lib/perl5

# Use difft for git diff if available
if [ -x /opt/homebrew/bin/difft ]; then
	export GIT_EXTERNAL_DIFF=/opt/homebrew/bin/difft
fi

# Set JAVA_HOME if zulu-17 is installed
if [ -d /Library/Java/JavaVirtualMachines/zulu-21.jdk/Contents/Home ]; then
	export JAVA_HOME=/Library/Java/JavaVirtualMachines/zulu-21.jdk/Contents/Home
fi

# --- Rust
alias cargo\ test="nocorrect cargo test"

if command -v gh &> /dev/null; then
	# eval "$(gh copilot alias -- zsh)"
	alias "??"="copilot -p"
fi
