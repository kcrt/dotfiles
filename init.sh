#!/bin/bash
set -e

# --------------------------------------------------------------
# Init script - set up my environment after OS clean installation
# To use:
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/kcrt/dotfiles/main/init.sh)"
# To re-run (with `bash -c`, the first argument becomes $0, hence the `_`):
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/kcrt/dotfiles/main/init.sh)" _ -f
# --------------------------------------------------------------

brew_packages=( adobe-acrobat-pro adobe-acrobat-reader afio appcleaner asciidoc atomicparsley atool audacity autoconf automake bartender bathyscaphe bchunk blender boost burn cabextract caffeine cairo calibre cgdb clamav clipy cmake cmigemo color-oracle coreutils cowsay cscope ctags ddd ddrescue dfc diff-so-fancy docbook duet emojify exiv2 fcrackzip ffmpeg figlet fontconfig fortune freetype fribidi fzf fzy gcc gdb gettext git glib gmp gnupg gnutls go google-chrome google-cloud-sdk grandperspective graphviz handbrake highlight htop icu4c imagemagick imageoptim inkscape iterm2 john jq karabiner-elements keepassxc kindle-comic-converter kotlin lame lha libdvdcss llvm lua luajit m-cli macgdbp mactex macvim mas meld zotero mosh musescore mutt nasm neovim nginx nkf nmap node numpy opencv openjpeg p11-kit p7zip pandoc pdfcrack peco pv pyenv python3 qlmarkdown r readline rstudio rsync sl blackhole-16ch sourcetree sqlite stow suspicious-package testdisk the_silver_searcher thefuck tigervnc-viewer tmux transmission tree tripmode vim vlc w3m webp wget x264 x265 xquartz xvid xz yarn yasm yt-dlp zbar zenity zsh zsh-syntax-highlighting iina atok forklift visual-studio-code zoom hammerspoon deepl lyrics-master menumeters docker bat ripgrep rustup bun deno uv pipx sheldon )
mas_packages=( 1206246482 1024640650 414855915 420874236 424389933 425424353 434290957 445189367 484757536 504700302 539883307 549083868 634148309 634159523 824171161 824183456 462054704 462058435 462062816 881418622 1547912640 921923693 451732904 1444383602 405399194 1342896380 441258766 928871589 )

# --------------------------------------------------------------

echo_color(){
	printf "\033[%sm" "$1"
	shift
	printf "%s\033[0m\n" "$*"
}
echo_red(){ echo_color "31" "$@"; }
echo_brightred(){ echo_color "01;31" "$@"; }
echo_aqua(){ echo_color "36" "$@"; }
echo_brightaqua(){ echo_color "01;36" "$@"; }

# Function to show whiptail selection dialog and return selected packages
# Usage: selected=$(select_packages_dialog "Title" pkg_info_array[@])
# Returns: space-separated list of selected packages
select_packages_dialog(){
	local title="$1"
	shift
	local pkg_info=("$@")

	local selected
	selected=$(whiptail --title "$title" --checklist "Please select packages to install." 0 0 0 "${pkg_info[@]}" 3>&1 1>&2 2>&3)
	echo "${selected//\"/}"
}

# Install only the apt packages that have an installation candidate.
# Unavailable ones (renamed or dropped in newer releases) are reported and skipped,
# so that a single stale name doesn't abort the whole run under `set -e`.
apt_install_available(){
	local available=()
	local p candidate
	for p in "$@"; do
		candidate=$(apt-cache policy "$p" 2>/dev/null | awk '/Candidate:/ {print $2}')
		if [ -n "$candidate" ] && [ "$candidate" != "(none)" ]; then
			available+=( "$p" )
		else
			echo_red "$p is not available. skipping..."
		fi
	done
	if [ ${#available[@]} -gt 0 ]; then
		sudo apt install "${available[@]}"
	fi
}

# --------------------------------------------------------------

clear
echo_aqua "kcrt's init script"
echo_aqua "    programmed by kcrt <kcrt@kcrt.net>"
echo_aqua "-----------------------------------------------------"
echo_aqua ""

if [ -f ~/dotfiles/init.sh ] && [ "$1" != "-f" ]; then
	echo_red "Probably, you had already executed this script."
	echo_red "If you really want to execute this script, please use -f option."
	exit
fi

if ! command -v sudo > /dev/null 2>&1; then
	echo_red "You need 'sudo' to execute this script."
	echo_red "Please install 'sudo' first."
	exit 1
fi

echo_aqua "Are you a member of sudoers? (y/N): "
read -r ans
if [ "$ans" != "y" ] ; then
	echo_aqua "This script needs 'sudo', and you need to be a member of the sudo group."
	echo_aqua "Adding $USER to the sudo group. Input the password of *root*..."
	su -c "/usr/sbin/usermod -aG sudo $USER"	# su keeps the user PATH, which lacks /usr/sbin
	echo_aqua "Please log out, log in again (to apply the group), and execute this script again!"
	exit
fi

echo_aqua "Testing 'sudo'..."
if ! sudo -v ; then
	echo "'sudo' failed. "
	echo "Please re-check /etc/sudoers and try again."
	exit
fi

echo_aqua "ok"


echo_aqua "(1/5) : Creating default directories ----------------"
mkdir -p ~/dotfiles
mkdir -p ~/bin
mkdir -p ~/src
mkdir -p ~/prog
mkdir -p ~/tmp
mkdir -p ~/.backup
mkdir -p ~/.trash
echo_aqua "ok."

echo_aqua "(2/5) : Application Installation --------------------"
if command -v brew > /dev/null 2>&1; then
	echo_aqua "Detected Homebrew..."
	# ---- Homebrew
	brew doctor || true	# exits 1 on any warning
	brew update

	brew install newt # for whiptail

	# for java
	brew install openjdk
	sudo ln -sfn "$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk" /Library/Java/JavaVirtualMachines/openjdk.jdk

	echo_aqua "Gathering information of brew packages.... This will take a few minutes."
	declare -a brew_info	# associative array doesn't work on macOS bash (because it's ver. 3)
	for p in "${brew_packages[@]}"; do
		if ! brew info "$p" >/dev/null 2>&1; then
			echo_red "$p is not available."
		else
			info=$(brew info "$p" | head -n2 | tail -n1)
			brew_info+=( "$p" )
			brew_info[${#brew_info[*]}]="${info}"
			brew_info+=( 1 )
		fi
	done

	brew_selected=$(select_packages_dialog "Homebrew packages" "${brew_info[@]}")
	# shellcheck disable=SC2206
	brew_selected=($brew_selected)
	for p in "${brew_selected[@]}"; do
		echo_aqua "Going to install: $p ..."
		brew install "$p" || echo_red "Failed to install: $p"
	done 

	echo "Do you want to install fonts? (Y/n)"
	read -r ans
	if [ "$ans" != "n" ] ; then
		brew install font-fira-code
		brew install font-ipaexfont
	fi
	
	# ---- Mac App Store
	echo "Going to install Mac App Store software"
	# mas can no longer check the sign-in state (`mas account` was removed)
	echo_aqua "Please sign in to the App Store, then push Enter."
	open "/System/Applications/App Store.app"
	read -r

	mas install 497799835 || echo_red "Failed to install: Xcode"	# Xcode
	# sudo xcodebuild -license
	echo_aqua "Gathering information of mac app store packages.... This will take a few minutes."
	declare -a mas_info	# associative array doesn't work on macOS bash (because it's ver. 3)
	for p in "${mas_packages[@]}"; do
		if ! ret=$(mas info "$p" 2>/dev/null); then
			echo_red "$p is not available."
		else
			info=$(echo "$ret" | head -n1)
			mas_info+=( "$p" )
			mas_info[${#mas_info[*]}]="${info}"
			mas_info+=( 1 )
		fi
	done

	mas_selected=$(select_packages_dialog "Mac App Store packages" "${mas_info[@]}")
	# shellcheck disable=SC2206
	mas_selected=($mas_selected)
	for p in "${mas_selected[@]}"; do
		echo_aqua "Going to install: $p ..."
		mas install "$p" || echo_red "Failed to install: $p"
	done 

elif [ "$(uname)" = "Darwin" ]; then
	echo_aqua "Homebrew not found!"
	echo_aqua "Please install homebrew first."
	open "https://brew.sh"
	echo_aqua "If ready, try again.";
	exit
elif [ -x /usr/bin/apt ]; then
	# ----- Debian, Ubuntu --------------------------------
	echo_aqua "Detected apt..."
	sudo apt update
	sudo apt upgrade
	sudo apt install locales
	sudo dpkg-reconfigure locales
	# ntpdate: not needed, systemd-timesyncd keeps the clock
	# cron-apt: superseded by unattended-upgrades (asked below)
	apt_install_available perl w3m zsh clamav tmux less rsync vim vim-common wget iputils-ping net-tools \
		manpages-ja nmap tcpdump fping atool lsof \
		hexer sl zip rdiff-backup ncurses-term ntfs-3g whois mutt git stow htop \
		apt-file fortune-mod mc dfc ccze pv python3 dstat \
		curl make nodejs g++ \
		ffmpeg \
		fzf fd-find bat zoxide direnv gh 7zip
	# Debian/Ubuntu ship bat, fd and 7zz (as Homebrew names it) as batcat, fdfind and 7z
	for cmd in bat:batcat fd:fdfind 7zz:7z; do
		if ! command -v "${cmd%%:*}" > /dev/null 2>&1 && command -v "${cmd#*:}" > /dev/null 2>&1; then
			ln -sf "$(command -v "${cmd#*:}")" ~/bin/"${cmd%%:*}"
		fi
	done
	echo "Current hostname is: $(hostname)"
	echo_aqua "Do you want to install and enable openssh-server? (y/N): "
	read -r ans
	if [ "$ans" = "y" ] ; then
		sudo apt install openssh-server
		sudo systemctl enable ssh
		sudo systemctl start ssh
		echo_aqua "SSH server installed and started. Current status:"
		sudo systemctl status ssh --no-pager
		echo_aqua ""
		echo_aqua "Do you want to add GitHub keys from https://github.com/kcrt.keys"
		echo_aqua "to authorized_keys? (y/N): "
		echo_red "Be careful! This will allow kcrt to access this machine via SSH."
		read -r ans
		if [ "$ans" = "y" ] ; then
			mkdir -p ~/.ssh
			chmod 700 ~/.ssh
			touch ~/.ssh/authorized_keys
			chmod 600 ~/.ssh/authorized_keys
			github_keys=$(curl -fsSL https://github.com/kcrt.keys)
			# Compare by key type + blob, not the whole line: keys imported by the Ubuntu
			# installer (ssh-import-id) carry a trailing comment, and lines may have options.
			while read -r key_type key_blob _; do
				[ -n "$key_blob" ] || continue
				if awk -v t="$key_type" -v b="$key_blob" \
					'{ for (i = 1; i < NF; i++) if ($i == t && $(i+1) == b) found = 1 } END { exit !found }' \
					~/.ssh/authorized_keys; then
					echo_aqua "Already registered: $key_type ${key_blob:0:16}..."
				else
					echo "$key_type $key_blob" >> ~/.ssh/authorized_keys
					echo_aqua "Added: $key_type ${key_blob:0:16}..."
				fi
			done <<< "$github_keys"
		fi
	fi
	echo_aqua "Do you install and enable avahi-daemon? (y/N): "
	read -r ans
	if [ "$ans" = "y" ] ; then
		sudo apt install avahi-daemon
		sudo systemctl enable avahi-daemon
		sudo systemctl start avahi-daemon
	fi

	echo_aqua "Do you want to set up unattended-upgrades? (y/N): "
	read -r ans
	if [ "$ans" = "y" ] ; then
		sudo apt install unattended-upgrades apt-listchanges
		sudo dpkg-reconfigure -plow unattended-upgrades
		echo_aqua "Please set e-mail address for information of unattended upgrades."
		echo_aqua "And set Automatic-Reboot to true if required."
		read -r ans
		sudo vim /etc/apt/apt.conf.d/50unattended-upgrades
	fi
	echo_aqua "Do you want to install msmtp for mail transfer? (y/N): "
	read -r ans
	if [ "$ans" = "y" ] ; then
		# msmtp instead of the unmaintained sSMTP; msmtp-mta provides /usr/sbin/sendmail
		sudo apt install msmtp msmtp-mta
		# msmtp ships no config file, so start from a template instead of an empty buffer
		if [ ! -f /etc/msmtprc ]; then
			sudo tee /etc/msmtprc > /dev/null <<-'EOF'
				# System-wide msmtp config (also used by /usr/sbin/sendmail via msmtp-mta)
				# Note: this file is world-readable; mind the password below.
				defaults
				auth           on
				tls            on
				tls_trust_file /etc/ssl/certs/ca-certificates.crt
				syslog         LOG_MAIL

				account        default
				host           smtp.example.com
				port           587
				from           you@example.com
				user           USERNAME
				password       PASSWORD
			EOF
		fi
		echo_aqua "Edit host / from / user / password in /etc/msmtprc. Push Enter to open vim."
		read -r
		sudo vim /etc/msmtprc
		echo_aqua "Test mail? (Your address): "
		read -r ans
		if [ "$ans" = "" ] ; then
			echo "skipping..."
		elif ! msmtp "$ans" <<-EOF
				To: $ans
				Subject: Test mail

				Hello world!
			EOF
		then
			echo_red "Test mail failed. Check /etc/msmtprc later (msmtp --serverinfo --account=default)."
		fi
	else
		echo_aqua "Please consider to install postfix or other MTAs."
	fi
	echo_aqua "Do you want to install GUI applications? (y/N): "
	read -r ans
	if [ "$ans" = "y" ] ; then
		# ubuntu-restricted-extras / chromium-browser exist only on Ubuntu, chromium only on Debian
		apt_install_available vlc ubuntu-restricted-extras chromium chromium-browser chromium-browser-l10n ibus-mozc
		if [ -d "$HOME/ドキュメント" ] ; then
			echo_aqua "renaming directory name into English..."
			LANG=C xdg-user-dirs-gtk-update
		fi
	fi
else
	echo_red "Unknown operating system."
	exit
fi

echo_aqua "(3/5) : Downloading and setting dot files -----------"
if [ -f ~/.ssh/id_ed25519 ]; then
	echo_aqua "key found."
else
	echo_aqua "generation public/secret keys..."
	ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519
fi
echo_aqua "If you use this machine with GitHub or other git servers, add this public key."
echo_aqua "(Not needed for the dotfiles below: they are cloned via https.)"
echo_aqua "-----"
cat ~/.ssh/id_ed25519.pub
echo_aqua "-----"
echo_aqua "push Enter to proceed."
read -r

if [ -d ~/dotfiles/.git ]; then
	git -C ~/dotfiles pull
else
	git clone --depth=1 https://github.com/kcrt/dotfiles.git ~/dotfiles
fi
cd ~/dotfiles
stow R asdf ccstatusline chawan claude cloudshell git hammerspoon mutt nethack opencode ripgrep ripgrep-all screen tmux vim zellij zsh

# neovim
# mkdir -p "${XDG_CONFIG_HOME:=$HOME/.config}"
# ln -s ~/.vim "$XDG_CONFIG_HOME"/nvim
# ln -s ~/.vimrc "$XDG_CONFIG_HOME"/nvim/init.vim

echo_aqua "(4/5) : Changing Default Shell ----------------------"
chsh -s "$(command -v zsh)"

echo_aqua "(5/5) : Optional Step -------------------------------"
echo_aqua "Do you want to install vim plugin manager vim-plug? (Y/n): "
read -r ans
if [ "$ans" != "n" ] ; then
	curl -fLo ~/.vim/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
	vim +PlugInstall +qall
fi

if ! command -v sheldon > /dev/null 2>&1 && ! [ -x ~/bin/sheldon ] && ! [ -x ~/.cargo/bin/sheldon ]; then
	echo_aqua "Do you want to install sheldon (zsh plugin manager) into ~/bin? (Y/n): "
	read -r ans
	if [ "$ans" != "n" ] ; then
		# Prebuilt binary: building with cargo needs OpenSSL headers, and Ubuntu's apt rustup is broken for `rustup run`
		curl --proto '=https' -fLsS https://rossmacarthur.github.io/install/crate.sh \
			| bash -s -- --repo rossmacarthur/sheldon --to ~/bin \
			|| echo_red "Failed to install sheldon. See https://sheldon.cli.rs/Installation.html"
	fi
fi

if [ "$(uname)" = "Darwin" ]; then
	echo_aqua "Mac OS X Setting..."

	# rga (ripgrep-all) on macOS reads config from ~/Library/Application Support,
	# not ~/.config. Symlink to keep dotfiles-managed config working.
	mkdir -p ~/Library/Application\ Support/ripgrep-all
	ln -sf ~/.config/ripgrep-all/config.jsonc \
		~/Library/Application\ Support/ripgrep-all/config.jsonc

	sudo nvram StartupMute=%01						# no boot sound
	defaults write -g AppleKeyboardUIMode -int 3				# Full keyboard access
	defaults write -g AppleShowAllExtensions -bool true			# Show file extentions
	defaults write -g InitialKeyRepeat -int 15				# time until key repeat
	defaults write -g KeyRepeat -int 2					# key repeat speed
	defaults write -g NSDocumentSaveNewDocumentsToCloud -bool false		# Don't save to cloud
	defaults write -g NSNavPanelExpandedStateForSaveMode -boolean true	# Expand save dialog
	defaults write -g PMPrintingExpandedStateForPrint2 -boolean true	# Expand print dialog
	defaults write -g WebKitDeveloperExtras -bool true
	defaults write -g com.apple.keyboard.fnState -bool true	# F1-F13 on external keyboard work as function keys
	defaults write -g com.apple.swipescrolldirection -bool false
	defaults write bluetoothaudiod "Enable AptX codec" -bool true
	defaults write com.apple.DiskUtility DUDebugMenuEnabled -bool true
	defaults write com.apple.DiskUtility advanced-image-options -bool true
	# Safari's preferences are sandboxed: writing them needs Full Disk Access for the terminal
	if ! {
		defaults write com.apple.Safari IncludeDevelopMenu -bool true &&
		defaults write com.apple.Safari IncludeInternalDebugMenu -bool true &&
		defaults write com.apple.Safari ShowFullURLInSmartSearchField -bool true &&
		defaults write com.apple.Safari ShowStatusBar -bool true &&
		defaults write com.apple.Safari WebKitDeveloperExtrasEnabledPreferenceKey -bool true &&
		defaults write com.apple.Safari com.apple.Safari.ContentPageGroupIdentifier.WebKit2DeveloperExtrasEnabled -bool true
	} 2>/dev/null; then
		echo_red "Could not write Safari settings. Grant Full Disk Access to the terminal and set them later."
	fi
	defaults write com.apple.TimeMachine DoNotOfferNewDisksForBackup -bool true
	defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
	defaults write com.apple.dock magnification -bool true
	defaults write com.apple.dock mouse-over-hilite-stack -bool true
	defaults write com.apple.dock wvous-bl-corner -int 5	# Start screen saver on bottom left corner
	defaults write com.apple.dock wvous-bl-modifier -int 0
	defaults write com.apple.finder FXPreferredViewStyle Nlsv		# Use list view for default
	defaults write com.apple.finder ShowPathbar -bool true
	defaults write com.apple.finder ShowStatusBar -bool true
	defaults write com.apple.finder ShowTabView -bool true
	defaults write com.apple.screencapture name "ScreenShot_"		# Screen shot file name
	defaults write com.apple.screencapture type -string "png"		# use png for screen shot
	defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad Clicking -bool true	# Tap to click
	defaults write -g ApplePressAndHoldEnabled -bool false	# Key repeat
	chflags nohidden ~/Library

fi
echo_aqua "OK! All settings done!"
echo_aqua "Recommend rebooting!"
