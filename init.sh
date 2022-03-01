#/bin/bash

# --------------------------------------------------------------
#
# Init script - set up my environment after OS clean install
#
# --------------------------------------------------------------

brew_packages=( adobe-acrobat-pro adobe-acrobat-reader afio appcleaner asciidoc atomicparsley atool audacity autoconf automake bartender bathyscaphe bchunk blender boost boost-python boxofsnoo-fairmount burn cabextract caffeine cairo calibre cgdb clamav clipy cmake cmigemo color-oracle coreutils cowsay cscope ctags ddd ddrescue dfc diff-so-fancy docbook duet emojify exiv2 fcrackzip ffmpeg figlet fontconfig fortune freetype fribidi fzf fzy gcc gdb gettext git glib gmp gnupg gnupg2 gnutls go google-chrome google-cloud-sdk grandperspective graphviz handbrake highlight htop icu4c imagemagick imageoptim inkscape iterm2 john jq karabiner-elements keepassxc kindle kindle-comic-converter  kotlin lame lepton lha libdvdcss linein llvm lua luajit m-cli macdown macgdbp mactex macvim mark-text mas meld mendeley mosh musescore mutt nasm neovim nginx nkf nmap node numpy opencv opencv3 openemu openjpeg osirix-quicklook p11-kit p7zip pandoc pdfcrack peco pv pyenv python3 qlcolorcode qlmarkdown qlprettypatch qlstephen quicklook-csv quicklook-json r rar readline rstudio rsync sequel-pro sl soundflower sourcetree sqlite suspicious-package testdisk the_silver_searcher thefuck tigervnc-viewer tmux transmission tree tripmode vim virtualbox vlc w3m webp wget x264 x265 xquartz xvid xz yarn yasm youtube-dl zbar zenity zsh zsh-syntax-highlighting iina atok forklift visual-studio-code zoom hammerspoon deepl lyrics-master menumeters)
mas_packages=( 1206246482 1024640650 414855915 420874236 424389933 425424353 434290957 445189367 484757536 504700302 539883307 549083868 634148309 634159523 824171161 824183456 462054704 462058435 462062816 881418622 1547912640 921923693 451732904 1444383602 405399194 1342896380 504700302 414855915 441258766  928871589)

# --------------------------------------------------------------

function echo_color(){
	# built-in echo in MacOS doesn't accept '-n' option
	/bin/echo -n "[$1m"
	shift
	/bin/echo "$@"
	/bin/echo -n "[0m"
}
function echo_red(){ echo_color "31" "$@"; }
function echo_brightred(){ echo_color "01;31" "$@"; }
function echo_aqua(){ echo_color "36" "$@"; }
function echo_brightaqua(){ echo_color "01;36" "$@"; }

# --------------------------------------------------------------

clear
echo_aqua "kcrt's init script"
echo_aqua "    programmed by kcrt <kcrt@kcrt.net>"
echo_aqua "-----------------------------------------------------"
echo_aqua ""

if [ -f ~/dotfiles/init.sh -a "$1" != "-f" ]; then
	echo_red "Probably, you had already executed this script."
	echo_red "If you really want to execute this script, please use -f option."
	exit
fi

if [ ! -x `which sudo` ]; then
	echo_red "You need 'sudo' to execute this script."
	echo_red "Please install 'sudo' first."
fi

echo_aqua "Are you a member of sudoers? (y/N): "
read ans
if [ "$ans" != "y" ] ; then
	echo_aqua "This script need 'sudo', and you need to be a member of sudoers."
	echo_aqua "Going to edit /etc/sudoers first."
	echo_aqua "Input the password of *root*, and execute visudo..."
	su
	echo_aqua "Please execute this script again!"
	exit
fi

echo_aqua "Testing 'sudo'..."
if [ `sudo echo 'test'` != 'test' ] ; then
	echo "'sudo' failed. "
	echo "Please re-check /etc/sudoers and try again."
	exit
fi

echo_aqua "ok"


echo_aqua "(1/5) : Creating default directories ----------------"
mkdir ~/dotfiles
mkdir ~/bin
mkdir ~/src
mkdir ~/prog
mkdir ~/tmp
mkdir ~/.backup
mkdir ~/.trash
echo_aqua "ok."

echo_aqua "(2/5) : Application Installation --------------------"
if [ -x /usr/bin/yum ] ; then
	# ----- Fedora, CentOS ---------------------------------
	OSType=Fedora
	echo_aqua "Detected yum..."
	sudo yum update
	sudo yum -y install perl zsh yum-utils vim-common vim-enhanced screen rsync subversion w3m yafc rdiff-backup fastest-mirror mutt clamav
elif [ -x `which brew` ]; then
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
	for p in ${brew_packages[@]}; do
		ret=`brew info "$p"`
		if [ $? -ne 0 ]; then
			echo_red "$p is not available."
		else
			info=`echo "$ret" | head -n2 | tail -n1`
			brew_info+=( $p )
			brew_info[${#brew_info[*]}]="${info}"
			brew_info+=( 1 )
		fi
	done

	selected=`whiptail --title "Homebrew packages" --checklist "Please select packages to install." 0 0 0  "${brew_info[@]}" 3>&1 1>&2 2>&3`
	selected=(`echo $selected |  sed s/'"'//g`)
	for p in ${selected[@]}; do
		echo_aqua "Going to install: $p ..."
		brew install $p
	done 

	echo "Do you want to install fonts? (Y/n)"
	read ans
	if [ "$ans" != "n" ] ; then
		brew install homebrew/cask-fonts/font-fira-code
		brew install font-ipaexfont
	fi
	
	# ---- Mac App Store
	echo "Going to install Mac App Store software"
	mas account
	if [ $? -ne 0 ] ; then
		echo_aqua "Please log-in to App Store."
		open "/System/Applications/App Store.app"
	fi
	mas account
	while [ $? -ne 0 ]; do
		sleep 5
		mas account
	done
	echo "Login confirmed."

	mas install 497799835 # Xcode
	# sudo xcodebuild -license
	echo_aqua "Gathering information of mac app store packages.... This will take a few minutes."
	declare -a mas_info	# associative array doesn't work on macOS bash (because it's ver. 3)
	for p in ${mas_packages[@]}; do
		ret=`mas info "$p"`
		if [ $? -ne 0 ]; then
			echo_red "$p is not available."
		else
			info=`echo "$ret" | head -n1`
			mas_info+=( $p )
			mas_info[${#mas_info[*]}]="${info}"
			mas_info+=( 1 )
		fi
	done

	selected=`whiptail --title "Mac App Store packages" --checklist "Please select packages to install." 0 0 0  "${mas_info[@]}" 3>&1 1>&2 2>&3`
	selected=(`echo $selected |  sed s/'"'//g`)
	for p in ${selected[@]}; do
		echo_aqua "Going to install: $p ..."
		mas install $p
	done 

elif [ `uname` = "Darwin" ]; then
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
	sudo apt -y upgrade
	sudo apt -y install locales
	sudo dpkg-reconfigure locales
	sudo apt -y install perl w3m zsh clamav screen less ntpdate rsync vim vim-common wget iputils-ping net-tools
	sudo apt -y install cron-apt ntpdate locales manpages-ja nmap netcat tcpdump fping atool lsof
	sudo apt -y install hexer yafc sl zip rdiff-backup ncurses-term ntfs-3g whois mutt git htop
	sudo apt -y install apt-file rhino fortune-mod mc dfc ccze pv python3 dstat
	sudo apt -y install curl make nodejs make g++
	sudo apt -y install ffmpeg
	sudo apt -y install unattended-upgrades
	sudo dpkg-reconfigure -plow unattended-upgrades
	echo_aqua "Please set e-mail address for information of unattended upgrades."
	read ans
	sudo vim /etc/apt/apt.conf.d/50unattended-upgrades
	echo_aqua "Do you want to install sSMTP for mail transfer? (y/N): "
	read ans
	if [ "$ans" = "y" ] ; then
		sudo aptitude -y install ssmpt
		sudo vim /etc/ssmtp/ssmtp.conf
		echo_aqua "Test mail? (Your address): "
		read ans
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
	read ans
	if [ "$ans" = "y" ] ; then
		sudo apt -y install adobe-flashplugin
		sudo apt -y install vlc
		sudo apt -y install ubuntu-restricted-extras
		sudo apt -y install chromium-browser chromium-browser-l10n chromium-codecs-ffmpeg-extra
		sudo apt -y install ibus-mozc
		if [ -d "~/ドキュメント" ] ; then
			echo_aqua "renaming directory name into English..."
			LANG=C; xdg-user-dirs-gtk-update
		fi
	fi
else
	echo_red "Unknown operating system."
	exit
fi

if [ -x "`which pyenv`" ]; then
	echo "pyenv:"
	pyenv install --list
	echo "Which environment do you want to install? (Package Name / n)"
	read ans
	if [ "$ans" != "n" ] ; then
		eval "$(pyenv init -)"
		pyenv install $ans
	fi
elif [ -x "`which python3`" ]; then
	python3 -m ensurepip --upgrade
fi

echo_aqua "(3/5) : Downloading and setting dot files -----------"
if [ -f ~/.ssh/id_rsa ]; then
	echo_aqua "key found."
else
	echo_aqua "generation public/secret keys..."
	ssh-keygen -t rsa
fi
echo_aqua "Please add this public key to gitolite of kcrt.net"
echo_aqua "-----"
cat ~/.ssh/id_rsa.pub
echo_aqua "-----"
echo_aqua "( add to keydir, and commit push to the repository )"
echo_aqua "push Enter to proceed."
read pause

cd ~
git clone https://github.com/kcrt/dotfiles.git
echo "Linking dotfiles..."
for file in ~/dotfiles/.*; do
	if [ -f $file ] ; then
		[ -f ~/$file:t ] && mv ~/$file:t ~/${file:t}.init
		ln -s $file ~/$file:t
	fi
done

# neovim
mkdir -p ${XDG_CONFIG_HOME:=$HOME/.config}
ln -s ~/.vim $XDG_CONFIG_HOME/nvim
ln -s ~/.vimrc $XDG_CONFIG_HOME/nvim/init.vim

echo_aqua "(4/5) : Changing Default Shell ----------------------"
chsh -s `which zsh`

echo_aqua "(5/5) : Optional Step -------------------------------"
echo_aqua "Do you want to install vim plugin manager Vundle? (Y/n): "
read ans
if [ "$ans" != "n" ] ; then
	mkdir ~/.vim
	git clone https://github.com/gmarik/vundle.git ~/.vim/bundle/Vundle.git
	vim -c ':PluginInstall' -c ':qall'
fi
echo_aqua "Do you need documents file like medical records and music sheets? (Y/n): "
read ans
if [ "$ans" != "n" ] ; then
	git clone --depth=1 ssh://git@kcrt.net:3122/kcrt/templates.git
	git clone --depth=1 ssh://git@kcrt.net:3122/kcrt/medical.git
	git clone --depth=1 ssh://git@kcrt.net:3122/kcrt/musicsheet.git
fi

if [ `uname` = "Darwin" ]; then
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
