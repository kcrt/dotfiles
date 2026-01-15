#
#	080-os_specific.zsh
#		macOS, Linux, and Cygwin specific settings
#

# ----- Fedora 固有設定
# alias :suspend="sudo /usr/sbin/pm-suspend"
# alias :hibernate="sudo /usr/sbin/pm-hibernate"

# ----- cygwin 固有設定
if [[ $OSTYPE = *cygwin* ]] ; then
	alias updatedb="updatedb --prunepaths='/cygdrive /proc'"
	alias open='cmd /c start '
	alias start='explorer . &'
fi

# ----- MacOS 固有設定
if [[ $OSTYPE = *darwin* ]] ; then
	# Set up man path if it exists
	[[ -d "/opt/local/man" ]] && export MANPATH=/opt/local/man:$MANPATH

	# Add LLVM and Android tools to path if they exist
	[[ -d "/usr/local/opt/llvm/bin" ]] && path=("/usr/local/opt/llvm/bin" $path)
	[[ -d "$HOME/Library/Android/sdk/platform-tools" ]] && path=($path "$HOME/Library/Android/sdk/platform-tools")

	# Set up common library flags for compilation
	# Note: Homebrew environment is already set up earlier in the file
	if [[ -n "$BIN_HOMEBREW" ]] ; then
		# Note: specifying multiple formulas at once takes too much time.
		for libname in readline zlib openssl@3 portaudio; do
			local lib_prefix="$($BIN_HOMEBREW --prefix $libname 2>/dev/null)"
			if [[ -d "$lib_prefix" ]]; then
				export LDFLAGS="-L$lib_prefix/lib $LDFLAGS"
				export CFLAGS="-I$lib_prefix/include $CFLAGS"
			fi
		done
	fi

	# Set up Xcode SDK path
	if [[ -x /usr/bin/xcrun ]]; then
		export SDKPATH=`xcrun --show-sdk-path`/usr/include
	fi

	# Set up pkg-config path
	if [[ -d "/usr/local/opt/libxml2/lib/pkgconfig" || -d "/usr/local/opt/zlib/lib/pkgconfig" ]]; then
		export PKG_CONFIG_PATH="/usr/local/opt/libxml2/lib/pkgconfig:/usr/local/opt/zlib/lib/pkgconfig"
	fi

	# Set Android SDK path if it exists
	[[ -d "$HOME/Library/Android/sdk" ]] && export ANDROID_SDK=$HOME/Library/Android/sdk

	# macOS specific aliases
	alias locate='mdfind -name'
	alias :sleep="pmset sleepnow"
	alias GetInProgress="mdfind 'kMDItemUserTags==InProgress'"
	alias SetInProgress="xattr -w com.apple.metadata:_kMDItemUserTags 'InProgress' "
	alias GetDeletable="mdfind 'kMDItemUserTags==Deletable'"
	alias SetDeletable="xattr -w com.apple.metadata:_kMDItemUserTags 'Deletable' "
	abbrev-alias sayen="say -v 'Ava (Premium)'"
	abbrev-alias sayuk="say -v Daniel"
	abbrev-alias sayjp="say -v 'Kyoko (Enhanced)'"
	abbrev-alias saych="say -v Tingting"
	alias QuickLook="qlmanage -p"
	alias :TimeMachineLog="log stream --style syslog --predicate 'senderImagePath contains[cd] \"TimeMachine\"' --info"
	alias HeySiri="open -a Siri"
	alias objdump="objdump --x86-asm-syntax=intel"
	alias zsh_on_rosetta="arch -x86_64 /bin/zsh"
	abbrev-alias gdb="arch -x86_64 gdb -q -ex 'set disassembly-flavor intel' -ex 'disp/i \$pc'"

	# Use MacVim's CLI version if available
	if [ -x "/usr/local/bin/mvim" ]; then
		alias vim="/usr/local/bin/mvim -v"
	fi

	# Add CotEditor to path if available
	if [ -x "/Applications/CotEditor.app/Contents/SharedSupport/bin/cot" ]; then
		alias cot="/Applications/CotEditor.app/Contents/SharedSupport/bin/cot"
	fi

	# Set up Google Cloud SDK if available
	if [ -d "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/" ]; then
		source "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc"
		source "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/completion.zsh.inc"
	fi

	if [ -x "/Applications/draw.io.app/Contents/MacOS/draw.io" ]; then
		alias draw.io=/Applications/draw.io.app/Contents/MacOS/draw.io
	fi

fi
