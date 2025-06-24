#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  maintain.sh
#         USAGE:  ./maintain.sh
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh
autoload zmv

case $HOST in
	aluminum.local)
		if [[ "`networksetup -getairportnetwork en0`" =~ nano* ]]; then
			;
		else
			OSError "Please execute this script at home (or use '-f')."
			if [[ "$1" != "-f" ]];then
				exit
			fi
		fi

		. "${DOTFILES}/routine/macos_brew_upgrade.sh"
		
		OSNotify "Anti-virus database updating..."
		freshclam
		OSNotify "Scanning system. This may take a while..."
		# clamscan --infected --cross-fs=no --recursive ~/Downloads # ~/Documents ~/Desktop

		# if command fails, pause and wait for user to press enter
		if [[ $? -ne 0 ]]; then
			OSError "!!! Virus found !!!"
			echo "Please check message. Press Enter key to continue..."
			read
		fi
		 
		# Before sending server, find Cargo.toml and execute cargo clean
		OSNotify "Cleaning up Rust projects..."
		cd ~/prog
		find . -name Cargo.toml -execdir cargo clean \;
		cd ~

		if [[ -d /Volumes/Backup/ ]]; then
			OSNotify "/Volumes/Backup/ mounted, refreshing QnapFileList.txt..."
			pv /Volumes/Backup/QnapFileList.txt | grep -v "AppleDouble" | grep -v "\._" | grep -v "DS_Store" | grep -v ".@__thumb" | LANG=C sort > ~/QnapFileList.txt
		else
			OSError "/Volumes/Backup not found."
		fi

		echo_info "==== Data back up and sync ===="
		. "${DOTFILES}/routine/aluminum_backup.sh"

		echo_info "==== recording (if available) ===="
		. "${DOTFILES}/routine/aluminum_recording.sh"
		
		echo_info "==== keepass ===="
		cp ~/Documents/passwords.kdbx ~/others/passwords.kdbx
		cp ~/Documents/passwords.kdbx "/Users/kcrt/Library/Mobile Documents/iCloud~be~kyuran~kypass2/Documents/passwords.kdbx"
		gsutil cp ~/Documents/passwords.kdbx gs://auto.backup.kcrt.net/auto/passwords.kdbx
		if [[ -e /Volumes/Backup/ ]]; then
			DATE=`date +%Y%m%d`
			cp ~/Documents/passwords.kdbx /Volumes/Backup/passwords/passwords-$DATE.kdbx
		fi
		
		OSNotify "Cleaning Caches..."
		hdfreebefore=`df -h / | grep / | awk '{print $4}'`
		cd ~/prog
		cd ~
		rm -rf ~/Library/Developer/Xcode/DerivedData/*
		rm -rf ~/Library/Developer/Xcode/iOS\ DeviceSupport/*
		rm -rf ~/Library/Developer/Xcode/Archives/*
		rm -rf ~/Library/Caches/com.apple.dt.Xcode/*
		rm -rf ~/Library/Developer/CoreSimulator/Caches/dyld/*
		xcrun simctl delete unavailable
		brew cleanup
		brew cleanup -s
		rm -rf /Users/kcrt/Library/Caches/Cypress/*
		hdfreeafter=`df -h / | grep / | awk '{print $4}'`
		OSNotify "Cleaned. Free space: $hdfreebefore -> $hdfreeafter"

		
		# echo_info "==== joplin ===="
		# joplin sync

		# echo_info "==== listing data on server ===="
		# gsutil ls -R gs://backup.kcrt.net/ | tee ~/gs_backup.txt
		;;
	*)
		echo_error "$HOST is unknown host!"
esac

echo_info "vim update"
vim -c "PluginInstall!" -c "qall"


. "${DOTFILES}/routine/r_install_packages.sh"

echo_info "Google cloud command update"
if [ -x `which gcloud` ]; then
	yes | gcloud components update
fi
pip3 install -U crcmod	# for gsutil rsync

echo_info "GitHub Copilot update"
if [ -x `which gh` ]; then
	gh extension upgrade gh-copilot
fi

echo_info "google key"
wget "https://pki.goog/roots.pem" -O ~/secrets/google-roots.pem

echo_info "FINISHED!"

