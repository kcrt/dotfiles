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

		# QNAP (Backup) -> Google Cloudに移行
		# OSNotify "prog -> Google Cloud"
		# LANG=ja_JP.UTF-8 gsutil -m rsync -x '.*\/(site-packages|\.git|\.DS_Store|\.tmp\.driveupload|venv|\.venv|\.pio|node_modules|dist|\.next|\.expo|\.mypy_cache)|Arduino\/libraries' -d -r ~/prog gs://auto.backup.kcrt.net/auto/prog
		# OSNotify "Documents -> Google Cloud"
		# LANG=ja_JP.UTF-8 gsutil -m rsync -x '.*\/(site-packages|\.git|\.DS_Store|\.tmp\.driveupload|venv|\.venv|\.pio|node_modules|dist|\.next|\.expo)|Arduino\/libraries' -d -r ~/Documents gs://auto.backup.kcrt.net/auto/documents
		# OSNotify "diskimage -> Google Cloud"
		# LANG=ja_JP.UTF-8 gsutil -m rsync -x "Tor.*\.sparsebundle" -d -r ~/diskimages/ gs://auto.backup.kcrt.net/auto/diskimages
		# OSNotify "Calibre -> Google Cloud"
		# LANG=ja_JP.UTF-8 gsutil -m rsync -d -r ~/Calibre/ gs://auto.backup.kcrt.net/auto/calibre
		# OSNotify "Pictures -> Google Cloud"
		# LANG=ja_JP.UTF-8 gsutil -m rsync -d -r ~/Pictures/ gs://auto.backup.kcrt.net/auto/pictures
		# OSNotify "Zotero -> Google Cloud"
		# LANG=ja_JP.UTF-8 gsutil -m rsync -d -r ~/Zotero/ gs://auto.backup.kcrt.net/auto/zotero
		
		# TODO: QNAP -> Google Cloudで定期バックアップ
		# OSNotify "books(drobo) -> Google Cloud"
		# LANG=ja_JP.UTF-8 gsutil -m rsync -d -r /Volumes/Main/books/ gs://auto.backup.kcrt.net/auto/books
		# OSNotify "HomeVideo(Drobo) -> Google Cloud"
		# gsutil -m rsync -d -r /Volumes/HomeVideo/Converted/ gs://auto.backup.kcrt.net/auto/convertedvideos
		# gsutil -m rsync -d -r /Volumes/HomeVideo/CamTemp/DCIM/ gs://auto.backup.kcrt.net/auto/videos

		. "${DOTFILES}/routine/aluminum_backup.sh"
		 

		echo_info "==== recording (if available) ===="
		if [[ -d /Volumes/Private/Recording/ ]]; then
			n=`ls $HOME/nosync/RecordingToSend/*.MP3 | wc -l`
			echo "There are $n mp3 file(s)."
			if [[ "$n" -ge 1 ]]; then
				zmv -v "$HOME/nosync/RecordingToSend/*_(*)_(*)A0.MP3" '/Volumes/Private/Recording/Recorder/$1_$2.MP3'
			fi
			n=`ls $HOME/nosync/RecordingToSend/*.m4a | wc -l`
			echo "There are $n m4a file(s)."
			if [[ "$n" -ge 1 ]]; then
				for m4afile in ~/nosync/RecordingToSend/*.m4a; do
					RECORDINGDATE=`ffprobe -loglevel quiet -of json -show_entries stream "$m4afile" | jq -r '.streams[0].tags.creation_time' | cut -c 1-19 | sed 's/:/-/g'`
					mv -v "$m4afile" "/Volumes/Private/Recording/VoiceMemo/${RECORDINGDATE}_${m4afile:t}"
				done
			fi
			for i in /Volumes/Private/Recording/VoiceMemo/*.m4a; do
				if [ ! -e "${i:r}.txt" ]; then
					echo "Whisper: $i"
					# Skip this temporary
					# whisper --language Japanese --model large -f txt "$i"
					# zmv -W "/Volumes/Private/Recording/VoiceMemo/*.m4a.txt" "/Volumes/Private/Recording/VoiceMemo/*.txt"
				fi
			done
		fi
		
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

