#!/bin/zsh

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
	nitrogen.local | oxygen.local | aluminum.local)
		OSNotify "macOS maintain script start"

		if [[ "`networksetup -getairportnetwork en0`" =~ nano* ]]; then
			;
		else
			OSError "Please execute this script at home (or use '-f')."
			if [[ "$1" != "-f" ]];then
				exit
			fi
		fi

		OSNotify "Updating brew..."
		brew update
		brew outdated
		brew upgrade
		brew cleanup
		brew cleanup -s
		brew bundle dump -f --file ${DOTFILES}/Brewfile

		OSNotify "Anti-virus database updating..."
		freshclam
		OSNotify "Scanning system. This may take a while..."
		clamscan --infected --cross-fs=no --recursive ~/Downloads # ~/Documents ~/Desktop

		# if command fails, pause and wait for user to press enter
		if [[ $? -ne 0 ]]; then
			OSError "!!! Virus found !!!"
			read -p "Please check message. Press [Enter] key to continue..."
		fi

		if [[ -e /Volumes/Main/ ]]; then
			OSNotify "/Volumes/Main/ mounted, refreshing VolumesMain.txt..."
			pv /Volumes/Main/DroboFileList.txt | grep -v "AppleDouble" | grep -v "\._" | grep -v "DS_Store" | LANG=C sort > ~/VolumeMain.txt
		else
			OSError "/Volumes/Main not found."
		fi

		echo_info "==== Data back up and sync ===="

		OSNotify "prog -> Google Cloud"
		LANG=ja_JP.UTF-8 gsutil -m rsync -x '.*\/(site-packages|\.git|\.DS_Store|\.tmp\.driveupload|venv|\.venv|\.pio|node_modules|dist|\.next|\.expo)|Arduino\/libraries' -d -r ~/prog gs://auto.backup.kcrt.net/auto/prog
		if [[ -d /Volumes/Main/shelter/ ]]; then
			OSNotify "prog -> Drobo"
			rsync -ahvz --exclude="site-packages/" --exclude=".git/" --exclude=".DS_Store" --exclude="packrat/" --exclude=".tmp.driveupload" --exclude="venv/" --exclude=".venv/" --exclude=".pio/" --exclude="node_modules/" --exclude="dist/" --exclude=".next/" --exclude=".expo" --exclude="Arduino/libraries/" --iconv=UTF-8,UTF-8-MAC --progress --delete --no-o --no-p --no-g --backup --backup-dir=/Volumes/Main/shelter/Trash ~/prog/ /Volumes/Main/shelter/backup/prog
		fi

		OSNotify "Documents -> Google Cloud"
		LANG=ja_JP.UTF-8 gsutil -m rsync -x '.*\/(site-packages|\.git|\.DS_Store|\.tmp\.driveupload|venv|\.venv|\.pio|node_modules|dist|\.next|\.expo)|Arduino\/libraries' -d -r ~/Documents gs://auto.backup.kcrt.net/auto/documents
		if [[ -d /Volumes/Main/shelter/ ]]; then
			OSNotify "Documents -> Drobo"
			rsync -ahvz --exclude="site-packages/" --exclude=".git/" --exclude=".DS_Store" --exclude="packrat/" --exclude=".tmp.driveupload" --exclude="venv/" --exclude=".venv/" --exclude=".pio/" --exclude="node_modules/" --exclude="dist/" --exclude=".next/" --exclude=".expo" --exclude="Arduino/libraries/" --iconv=UTF-8,UTF-8-MAC --progress --delete --no-o --no-p --no-g --backup --backup-dir=/Volumes/Main/shelter/Trash ~/Documents/ /Volumes/Main/shelter/backup/documents
		fi

		OSNotify "diskimage -> Google Cloud"
		LANG=ja_JP.UTF-8 gsutil -m rsync -x "Tor.*\.sparsebundle" -d -r ~/diskimages/ gs://auto.backup.kcrt.net/auto/diskimages
		if [[ -d /Volumes/Private/diskimages/ ]]; then
			OSNotify "diskimage -> Drobo (Private)"
			rsync -ahv --progress --delete ~/diskimages/ /Volumes/Private/backup/diskimages
		fi

		if [[ -d /Volumes/Main/books/ ]]; then
			OSNotify "books(Drobo) -> Google Cloud"
			LANG=ja_JP.UTF-8 gsutil -m rsync -d -r /Volumes/Main/books/ gs://auto.backup.kcrt.net/auto/books
		fi

		OSNotify "Calibre -> Google Cloud"
		LANG=ja_JP.UTF-8 gsutil -m rsync -d -r ~/Calibre\ Library/ gs://auto.backup.kcrt.net/auto/calibre
		if [[ -d /Volumes/Main/ ]]; then
			OSNotify "Calibre -> drobo"
			rsync -ahv --progress --delete ~/Calibre\ Library/ /Volumes/Private/backup/Calibre\ Library
		fi

		if [[ -d /Volumes/eee/ && -d /Volumes/Private/comic/eee/ ]]; then
			OSNotify "eee (mounted) -> Drobo"
			rsync -ahv --iconv=UTF-8,UTF-8-MAC --progress --delete /Volumes/eee/comics/ /Volumes/Private/backup/eee/
		fi

		OSNotify "Pictures -> Google Cloud"
		LANG=ja_JP.UTF-8 gsutil -m rsync -d -r ~/Pictures/ gs://auto.backup.kcrt.net/auto/pictures
		if [[ -d /Volumes/Private/ ]]; then
			OSNotify "Pictures -> drobo"
			rsync -ahv --progress --delete ~/Pictures/ /Volumes/Private/backup/pictures
		fi

		OSNotify "Zotero -> Google Cloud"
		LANG=ja_JP.UTF-8 gsutil -m rsync -d -r ~/Zotero/ gs://auto.backup.kcrt.net/auto/zotero
		if [[ -d /Volumes/Main/ ]]; then
			OSNotify "Zotero -> drobo"
			rsync -ahv --progress --delete ~/Zotero/ /Volumes/Main/shelter/backup/Zotero
		fi

		if [[ -e /Volumes/HomeVideo/ ]]; then
			OSNotify "HomeVideo(Drobo) -> Google Cloud"
			gsutil -m rsync -d -r /Volumes/HomeVideo/Converted/ gs://auto.backup.kcrt.net/auto/convertedvideos
			gsutil -m rsync -d -r /Volumes/HomeVideo/CamTemp/DCIM/ gs://auto.backup.kcrt.net/auto/videos
		fi

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
					zmv -W "/Volumes/Private/Recording/VoiceMemo/*.m4a.txt" "/Volumes/Private/Recording/VoiceMemo/*.txt"
				fi
			done
		fi
		
		echo_info "==== keepass ===="
		cp ~/Documents/passwords.kdbx ~/others/passwords.kdbx
		cp ~/Documents/passwords.kdbx "/Users/kcrt/Library/Mobile Documents/iCloud~be~kyuran~kypass2/Documents/passwords.kdbx"
		gsutil cp ~/Documents/passwords.kdbx gs://auto.backup.kcrt.net/auto/passwords.kdbx
		if [[ -e /Volumes/Main/ ]]; then
			DATE=`date +%Y%m%d`
			cp ~/Documents/passwords.kdbx /Volumes/Main/shelter/passwords/passwords-$DATE.kdbx
		fi
		
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

# echo_info "Bioconductor update"
# R --vanilla << BIO_UPDATE
# source("http://bioconductor.org/biocLite.R")
# biocLite()
# biocLite("GEOquery")
# biocLite("impute")
# BIO_UPDATE
echo_info "R update"
R --vanilla << R_UPDATE
options(repos=c(CRAN="http://cran.r-project.org"))
packages_to_need = c("tidyverse")
packages_installed = rownames(installed.packages())
packages_to_install = packages_to_need[!is.element(packages_to_need, packages_installed)]
install.packages(packages_to_install, dependencies=TRUE)
update.packages(ask=FALSE)
R_UPDATE

echo_info "Google cloud command update"
if [ -x `which gcloud` ]; then
	yes | gcloud components update
fi
pip3 install -U crcmod	# for gsutil rsync

echo_info "google key"
wget "https://pki.goog/roots.pem" -O ~/secrets/google-roots.pem

echo_info "FINISHED!"

