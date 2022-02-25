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
		# OSNotify "Scanning system..."
		# clamd &
		# sleep 5
		# clamdscan -m ~

		if [[ -e /Volumes/Main/ ]]; then
			OSNotify "/Volumes/Main/ mounted, refreshing VolumesMain.txt..."
			pv /Volumes/Main/DroboFileList.txt | grep -v "AppleDouble" | grep -v "\._" | grep -v "DS_Store" | LANG=C sort > ~/VolumeMain.txt
		else
			OSError "/Volumes/Main not found."
		fi

		echo_info "==== Data back up and sync ===="
		OSNotify "Medical -> Google Cloud"
		LANG=ja_JP.UTF-8 gsutil -m rsync -x ".*site-packages.*|\.git|\.DS_Store" -d -r ~/Documents/医療 gs://backup.kcrt.net/manual/document_medical
		if [[ -d /Volumes/Main/shelter/ ]]; then
			OSNotify "Medical -> Drobo"
			rsync -ahvz --exclude="site-packages/" --exclude=".git/" --exclude="packrat/" --iconv=UTF-8,UTF-8-MAC --progress --delete --no-o --no-p --no-g --backup --backup-dir=/Volumes/Main/shelter/Trash ~/Documents/医療 /Volumes/Main/shelter/medical
		fi

		OSNotify "diskimage -> Google Cloud"
		LANG=ja_JP.UTF-8 gsutil -m rsync -d -r ~/diskimages/ gs://backup.kcrt.net/manual/diskimages

		if [[ -d /Volumes/Private/diskimages/ ]]; then
			OSNotify "diskimage -> Drobo"
			rsync -ahv --progress --delete ~/diskimages /Volumes/Private/diskimages/
		fi
		
		if [[ -d /Volumes/Main/books/ ]]; then
			OSNotify "books(Drobo) -> Google Cloud"
			LANG=ja_JP.UTF-8 gsutil -m rsync -r /Volumes/Main/books gs://backup.kcrt.net/manual/books
		fi

		if [[ -d /Volumes/eee/ && -d /Volumes/Private/comic/eee/ ]]; then
			OSNotify "eee (mounted) -> Drobo"
			rsync -ahv --iconv=UTF-8,UTF-8-MAC --progress --delete /Volumes/eee/comics /Volumes/Private/comic/eee/
		fi

		OSNotify "Pictures -> drobo"
		rsync -ahv --progress --delete ~/Pictures /Volumes/Private/pictures
		OSNotify "Pictures -> Google cloud"
		LANG=ja_JP.UTF-8 gsutil -m rsync -d -r ~/Pictures gs://backup.kcrt.net/manual/pictures

		if [[ -e /Volumes/HomeVideo/ ]]; then
			OSNotify "HomeVideo(Drobo) -> Google Cloud"
			gsutil -m rsync -d -r /Volumes/HomeVideo/Converted gs://backup.kcrt.net/manual/convertedvideos
			gsutil -m rsync -d -r /Volumes/HomeVideo/CamTemp/DCIM gs://backup.kcrt.net/manual/videos
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
					RECORDINGDATE=`ffprobe -loglevel quiet -of json -show_entries stream "$m4afile" | jq -r '.streams[0].tags.creation_time' | cut -c 1-19`
					mv -v "$m4afile" "/Volumes/Private/Recording/VoiceMemo/${RECORDINGDATE}_${m4afile:t}"
				done
			fi
		fi
		
		echo_info "==== keepass ===="
		cp ~/passwords.kdbx ~/others/passwords.kdbx
		cp ~/passwords.kdbx "/Users/kcrt/Library/Mobile Documents/iCloud~be~kyuran~kypass2/Documents/passwords.kdbx"
		gsutil cp ~/passwords.kdbx gs://backup.kcrt.net/manual/passwords.kdbx
		if [[ -e /Volumes/Main/ ]]; then
			cp ~/passwords.kdbx /Volumes/Main/shelter/passwords.kdbx
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
packages_to_need = c("tidyverse", "gdata", "agricolae", "car", "extrafont", "ggplot2", "coin", "Epi", "irr", "minerva", "coefplot", "pROC", "Cairo", "samr", "inline", "Rcpp", "readxl", "MatchIt", "epiDisplay", "psych", "rstan")
packages_installed = rownames(installed.packages())
packages_to_install = packages_to_need[!is.element(packages_to_need, packages_installed)]
install.packages(packages_to_install, dependencies=TRUE)
update.packages(ask=FALSE)
R_UPDATE

echo_info "Google cloud command update"
if [ -x `which gcloud` ]; then
	yes | gcloud components update
fi

echo_info "google key"
wget "https://pki.goog/roots.pem" -O ~/secrets/google-roots.pem

echo_info "FINISHED!"

