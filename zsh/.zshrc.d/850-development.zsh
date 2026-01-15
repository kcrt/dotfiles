#
#	095-development.zsh
#		Mise, Rust, Perl, Java, GitHub Copilot
#

# ===== Develop
if [[ $OSTYPE = *darwin* ]] ; then
	# mise (formerly rtx) - faster alternative to asdf
	if command -v mise >/dev/null 2>&1; then
		eval "$(mise activate zsh)"

		# Note: RUBY_CONFIGURE_OPTS is disabled because brew --prefix is very slow (~20s)
		# Uncomment only if you need to build Ruby from source:
		# export RUBY_CONFIGURE_OPTS="--with-openssl-dir=$($BIN_HOMEBREW --prefix openssl@1.1)"
	fi
fi

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
