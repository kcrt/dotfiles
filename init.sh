#!/bin/bash
set -e

# --------------------------------------------------------------
# Init script - set up my environment after OS clean installation
# To use:
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/kcrt/dotfiles/main/init.sh)"
# --------------------------------------------------------------

brew_packages=( adobe-acrobat-pro adobe-acrobat-reader afio appcleaner asciidoc atomicparsley atool audacity autoconf automake bartender bathyscaphe bchunk blender boost burn cabextract caffeine cairo calibre cgdb clamav clipy cmake cmigemo color-oracle coreutils cowsay cscope ctags ddd ddrescue dfc diff-so-fancy docbook duet emojify exiv2 fcrackzip ffmpeg figlet fontconfig fortune freetype fribidi fzf fzy gcc gdb gettext git glib gmp gnupg gnupg2 gnutls go google-chrome google-cloud-sdk grandperspective graphviz handbrake highlight htop icu4c imagemagick imageoptim inkscape iterm2 john jq karabiner-elements keepassxc kindle kindle-comic-converter  kotlin lame lepton lha libdvdcss linein llvm lua luajit m-cli macdown macgdbp mactex macvim mark-text mas meld zotero mosh musescore mutt nasm neovim nginx nkf nmap node numpy opencv opencv3 openemu openjpeg osirix-quicklook p11-kit p7zip pandoc pdfcrack peco pv pyenv python3 qlcolorcode qlmarkdown qlprettypatch qlstephen quicklook-csv quicklook-json r rar readline rstudio rsync sequel-pro sl blackhole-16ch sourcetree sqlite suspicious-package testdisk the_silver_searcher thefuck tigervnc-viewer tmux transmission tree tripmode vim vlc w3m webp wget x264 x265 xquartz xvid xz yarn yasm yt-dlp zbar zenity zsh zsh-syntax-highlighting iina atok forklift visual-studio-code zoom hammerspoon deepl lyrics-master menumeters docker bat ripgrep rustup bun deno uv pipx )
mas_packages=( 1206246482 1024640650 414855915 420874236 424389933 425424353 434290957 445189367 484757536 504700302 539883307 549083868 634148309 634159523 824171161 824183456 462054704 462058435 462062816 881418622 1547912640 921923693 451732904 1444383602 405399194 1342896380 504700302 414855915 441258766  928871589)

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

	selected=$(whiptail --title "$title" --checklist "Please select packages to install." 0 0 0 "${pkg_info[@]}" 3>&1 1>&2 2>&3)
	echo "${selected//\"/}"
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

if [ ! -x "$(which sudo)" ]; then
	echo_red "You need 'sudo' to execute this script."
	echo_red "Please install 'sudo' first."
fi

echo_aqua "Are you a member of sudoers? (y/N): "
read -r ans
if [ "$ans" != "y" ] ; then
	echo_aqua "This script need 'sudo', and you need to be a member of sudoers."
	echo_aqua "Going to edit /etc/sudoers first."
	echo_aqua "Input the password of *root*, and execute visudo..."
	# shellcheck disable=SC2117
	su
	echo_aqua "Please execute this script again!"
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
[ ! -d ~/dotfiles ] && mkdir ~/dotfiles
[ ! -d ~/bin ] && mkdir ~/bin
[ ! -d ~/src ] && mkdir ~/src
[ ! -d ~/prog ] && mkdir ~/prog
[ ! -d ~/tmp ] && mkdir ~/tmp
[ ! -d ~/.backup ] && mkdir ~/.backup
[ ! -d ~/.trash ] && mkdir ~/.trash
echo_aqua "ok."

echo_aqua "(2/5) : Application Installation --------------------"
if [ -x /usr/bin/yum ] ; then
	# ----- Fedora, CentOS ---------------------------------
	OSType=Fedora
	echo_aqua "Detected yum..."
	sudo yum update
	sudo yum -y install perl zsh yum-utils vim-common vim-enhanced screen rsync subversion w3m yafc rdiff-backup fastest-mirror mutt clamav
elif [ -x "$(which brew)" ]; then
	OSType=HomeBrew
	echo_aqua "Detected Homebrew..."
	# ---- Homebrew
	brew doctor
	brew update

	brew install newt # for whiptail

	# for java
	brew install openjdk
	sudo ln -sfn /usr/local/opt/openjdk/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk.jdk

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

	selected=$(select_packages_dialog "Homebrew packages" "${brew_info[@]}")
	# shellcheck disable=SC2206
	selected=($selected)
	for p in "${selected[@]}"; do
		echo_aqua "Going to install: $p ..."
		brew install "$p"
	done 

	echo "Do you want to install fonts? (Y/n)"
	read -r ans
	if [ "$ans" != "n" ] ; then
		brew install font-fira-code
		brew install font-ipaexfont
	fi
	
	# ---- Mac App Store
	echo "Going to install Mac App Store software"
	if ! mas account ; then
		echo_aqua "Please log-in to App Store."
		open "/System/Applications/App Store.app"
	fi
	while ! mas account; do
		sleep 5
		mas account
	done
	echo "Login confirmed."

	mas install 497799835 # Xcode
	# sudo xcodebuild -license
	echo_aqua "Gathering information of mac app store packages.... This will take a few minutes."
	declare -a mas_info	# associative array doesn't work on macOS bash (because it's ver. 3)
	for p in "${mas_packages[@]}"; do
		ret=$(mas info "$p")
		if [ "$?" -ne 0 ]; then
			echo_red "$p is not available."
		else
			info=$(echo "$ret" | head -n1)
			mas_info+=( "$p" )
			mas_info[${#mas_info[*]}]="${info}"
			mas_info+=( 1 )
		fi
	done

	selected=$(select_packages_dialog "Mac App Store packages" "${mas_info[@]}")
	# shellcheck disable=SC2206
	selected=($selected)
	for p in "${selected[@]}"; do
		echo_aqua "Going to install: $p ..."
		mas install "$p"
	done 

elif [ "$(uname)" = "Darwin" ]; then
	echo_aqua "Homebrew not found!"
	echo_aqua "Please install homebrew first."
	open "https://brew.sh"
	read ans
	echo_aqua "If ready, try again.";
	exit
elif [ -x /usr/bin/apt ]; then
	# ----- Debian, Ubuntu --------------------------------
	OSType=Debian
	echo_aqua "Detected apt..."
	sudo apt update
	sudo apt upgrade
	sudo apt install locales
	sudo dpkg-reconfigure locales
	sudo apt install perl w3m zsh clamav tmux less ntpdate rsync vim vim-common wget iputils-ping net-tools
	sudo apt install cron-apt locales manpages-ja nmap tcpdump fping atool lsof
	sudo apt install hexer yafc sl zip rdiff-backup ncurses-term ntfs-3g whois mutt git htop
	sudo apt install apt-file rhino fortune-mod mc dfc ccze pv python3 dstat
	sudo apt install curl make nodejs make g++
	sudo apt install ffmpeg
	echo "Current hostname is: $(hostname)"
	echo_aqua "Do you want to install and enable openssh-server? (y/N): "
	read -r ans
	if [ "$ans" = "y" ] ; then
		sudo apt install openssh-server
		sudo systemctl enable ssh
		sudo systemctl start ssh
		echo_aqua "SSH server installed and started. Current status:"
		sudo systemctl status ssh --no-pager
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
	echo_aqua "Do you want to install sSMTP for mail transfer? (y/N): "
	read -r ans
	if [ "$ans" = "y" ] ; then
		sudo apt install ssmtp
		sudo vim /etc/ssmtp/ssmtp.conf
		echo_aqua "Test mail? (Your address): "
		read -r ans
		if [ "$ans" = "" ] ; then
			echo "skipping..."
		else
			ssmtp "$ans" << EOF
To: $ans
From: kcrtrg@kcrt.net
Subject: Test mail

Hello world!
EOF
		fi
	else
		echo_aqua "Please consider to install postfix or other MTAs."
	fi
	echo_aqua "Do you want to install GUI applications? (y/N): "
	read -r ans
	if [ "$ans" = "y" ] ; then
		sudo apt-get install adobe-flashplugin
		sudo apt-get install vlc
		sudo apt-get install ubuntu-restricted-extras
		sudo apt-get install chromium-browser chromium-browser-l10n chromium-codecs-ffmpeg-extra
		sudo apt-get install ibus-mozc
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
	ssh-keygen -t ed25519
fi
echo_aqua "Please add this public key to github"
echo_aqua "-----"
cat ~/.ssh/id_ed25519.pub
echo_aqua "-----"
echo_aqua "push Enter to proceed."
read -r pause

cd ~
git clone --depth=1 https://github.com/kcrt/dotfiles.git
~/dotfiles/script/link_dots.sh

# neovim
mkdir -p "${XDG_CONFIG_HOME:=$HOME/.config}"
ln -s ~/.vim "$XDG_CONFIG_HOME"/nvim
ln -s ~/.vimrc "$XDG_CONFIG_HOME"/nvim/init.vim

echo_aqua "(4/5) : Changing Default Shell ----------------------"
chsh -s $(which zsh)

echo_aqua "(5/5) : Optional Step -------------------------------"
echo_aqua "Do you want to install vim plugin manager Vundle? (Y/n): "
read -r ans
if [ "$ans" != "n" ] ; then
	mkdir ~/.vim
	git clone https://github.com/gmarik/vundle.git ~/.vim/bundle/Vundle.git
	vim -c ':PluginInstall' -c ':qall'
fi

if [ "$(uname)" = "Darwin" ]; then
	echo_aqua "Mac OS X Setting..."
	sudo nvram SystemAudioVolume=%00					# no boot sound
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
	defaults write com.apple.Safari IncludeDevelopMenu -bool true
	defaults write com.apple.Safari IncludeInternalDebugMenu -bool true
	defaults write com.apple.Safari ShowFullURLInSmartSearchField -bool true
	defaults write com.apple.Safari ShowStatusBar -bool true
	defaults write com.apple.Safari WebKitDeveloperExtrasEnabledPreferenceKey -bool true
	defaults write com.apple.Safari com.apple.Safari.ContentPageGroupIdentifier.WebKit2DeveloperExtrasEnabled -bool true
	defaults write com.apple.TimeMachine DoNotOfferNewDisksForBackup -bool true
	defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
	defaults write com.apple.dock magnification -bool true
	defaults write com.apple.dock mouse-over-hilite-stack -bool true
	defaults write com.apple.dock wvous-bl-corner -int 5	# Start screen saver on bottom left corner
	defaults write com.apple.dock wvous-bl-modifier -int 0
	defaults write com.apple.finder FXPreferredViewStyle Nlsv		# Use list view for default
	defaults write com.apple.finder QLEnableTextSelection -bool true	# Enable text selection on quicklook
	defaults write com.apple.finder ShowPathbar -bool true
	defaults write com.apple.finder ShowStatusBar -bool true
	defaults write com.apple.finder ShowTabView -bool true
	defaults write com.apple.menuextra.battery ShowPercent -string "YES"
	defaults write com.apple.screencapture name "ScreenShot_"		# Screen shot file name
	defaults write com.apple.screencapture type -string "png"		# use png for screen shot
	defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad Clicking -bool true	# Tap to click
	defaults write -g ApplePressAndHoldEnabled -bool false	# Key repeat
	chflags nohidden ~/Library

fi
echo_aqua "OK! All settings done!"
echo_aqua "Recommend rebooting!"
