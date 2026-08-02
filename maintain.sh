#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  maintain.sh
#         USAGE:  ./maintain.sh
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

# Everything here is addressed relative to $DOTFILES, and the helpers below
# (echo_info, OSNotify, ...) come from it. Bail out before anything else if it
# is missing, otherwise the failure surfaces much later as "command not found".
if [[ ! -r "${DOTFILES}/script/OSNotify.sh" ]]; then
	echo "maintain.sh: \$DOTFILES is not set correctly (DOTFILES=${DOTFILES:-<unset>})." >&2
	echo "Please export it to your dotfiles directory, e.g. export DOTFILES=~/dotfiles" >&2
	exit 1
fi

source ${DOTFILES}/script/OSNotify.sh
autoload zmv

# Routines exit on their own error paths (e.g. "QNAP is not reachable"), so run
# them in a subshell; otherwise their exit would terminate maintain.sh itself.
run_routine(){
	local routine="${DOTFILES}/routine/$1"
	if [[ ! -r "$routine" ]]; then
		OSError "Routine not found: $1"
		return 1
	fi
	( . "$routine" )
}

case $HOST in
	aluminum.local)
		# Almost everything below needs the NAS at home, so its reachability is
		# what "am I at home?" actually means here.
		if ! ping -c 1 qnap.local &> /dev/null; then
			OSError "qnap.local is not reachable. Please execute this script at home."
			exit 1
		fi

		run_routine macos_brew_upgrade.sh

		run_routine generic_clamscan_update_and_scan.sh

		# Before sending server, find Cargo.toml and execute cargo clean
		OSNotify "Cleaning up Rust projects..."
		(
			cd ~/prog || exit 1
			# Prune build artifacts and vendored crates; they contain their own
			# Cargo.toml but are not projects of ours.
			find . \( -name target -o -name node_modules -o -name .git \) -prune \
				-o -name Cargo.toml -execdir cargo clean \;
		)

		if [[ -d /Volumes/Backup/ ]]; then
			OSNotify "/Volumes/Backup/ mounted, refreshing QnapFileList.txt..."
			pv /Volumes/Backup/QnapFileList.txt | grep -Ev 'AppleDouble|\._|DS_Store|\.@__thumb' | LANG=C sort > ~/QnapFileList.txt
		else
			OSError "/Volumes/Backup not found."
		fi

		echo_info "==== Data back up and sync ===="
		run_routine aluminum_backup.sh

		echo_info "==== recording (if available) ===="
		run_routine aluminum_recording.sh

		echo_info "==== keepass ===="
		# The password database is the most important thing we copy around, so
		# every destination is verified and any failure is reported loudly.
		KEEPASS_DB=~/Documents/passwords.kdbx
		KEEPASS_GENERATIONS=20
		backup_keepass(){
			local dest="$1"
			if [[ ! -d "${dest:h}" ]]; then
				OSError "KeePass backup directory not found: ${dest:h}"
				return 1
			fi
			if cp "$KEEPASS_DB" "$dest"; then
				echo_ok "passwords.kdbx -> $dest"
			else
				OSError "Failed to copy passwords.kdbx to $dest"
				return 1
			fi
		}
		if [[ ! -f "$KEEPASS_DB" ]]; then
			OSError "$KEEPASS_DB not found. Skipping password backup."
		else
			backup_keepass "$HOME/Library/Mobile Documents/iCloud~be~kyuran~kypass2/Documents/passwords.kdbx"
			if gcloud storage cp "$KEEPASS_DB" gs://auto.backup.kcrt.net/auto/passwords.kdbx; then
				echo_ok "passwords.kdbx -> gs://auto.backup.kcrt.net/auto/"
			else
				OSError "Failed to upload passwords.kdbx to Google Cloud Storage."
			fi
			if [[ -d /Volumes/Backup/passwords ]]; then
				if backup_keepass "/Volumes/Backup/passwords/passwords-$(date +%Y%m%d).kdbx"; then
					# (NOn): skip if empty, sort by name descending == newest first
					kdbx_generations=(/Volumes/Backup/passwords/passwords-*.kdbx(NOn))
					if (( ${#kdbx_generations} > KEEPASS_GENERATIONS )); then
						echo_info "Removing $(( ${#kdbx_generations} - KEEPASS_GENERATIONS )) old generation(s) of passwords.kdbx..."
						rm -v -f -- "${kdbx_generations[@]:$KEEPASS_GENERATIONS}"
					fi
				fi
			else
				OSError "/Volumes/Backup/passwords not found. Skipping dated backup."
			fi
		fi


		OSNotify "Cleaning Caches..."
		hdfreebefore=$(df -h / | awk 'NR==2 {print $4}')
		cd ~
		# Glob qualifier (ND) on the rm patterns below:
		#   N ... nullglob. Without it zsh aborts the rm with "no matches found"
		#         whenever the directory is already empty or missing.
		#   D ... glob dots. Also match .DS_Store and friends ('.' and '..' are
		#         never included, so this is safe to pass to rm -rf).
		# Xcode
		rm -rf ~/Library/Developer/Xcode/DerivedData/*(ND)
		rm -rf ~/Library/Developer/Xcode/iOS\ DeviceSupport/*(ND)
		rm -rf ~/Library/Developer/Xcode/Archives/*(ND)
		rm -rf ~/Library/Caches/com.apple.dt.Xcode/*(ND)
		rm -rf ~/Library/Developer/CoreSimulator/Caches/dyld/*(ND)
		xcrun simctl delete unavailable
		# Homebrew
		brew autoremove
		brew cleanup -s --prune=1
		# Node.js / JavaScript
		npm cache clean --force
		rm -rf ~/Library/Caches/node-gyp
		pnpm store prune
		bun pm cache rm
		# --yes: never stop for npx's "install playwright?" prompt.
		# --all: 'uninstall' takes no positional argument; the flag is what
		#        removes browsers of every Playwright installation.
		npx --yes playwright uninstall --all
		rm -rf ~/Library/Caches/Cypress/*(ND)
		# Python
		pip3 cache purge
		uv cache clean
		# Rust (registry cache only, keep toolchains)
		cargo cache -a
		# Go
		go clean -modcache
		hdfreeafter=$(df -h / | awk 'NR==2 {print $4}')
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
# .vimrc uses vim-plug (PluginInstall is Vundle's command and does not exist).
# --sync is required so that the updates finish before vim quits.
vim -c "PlugInstall --sync" -c "PlugUpdate --sync" -c "qall"


run_routine generic_r_install_packages.sh

echo_info "Google cloud command update"
if command -v gcloud > /dev/null 2>&1; then
	yes | gcloud components update
fi

echo_info "GitHub Copilot update"
if command -v gh > /dev/null 2>&1; then
	gh extension upgrade gh-copilot
fi

echo_info "google key"
# wget -O truncates the destination before it even connects, so download to a
# temporary file and replace the existing pem only after a successful download.
roots_pem_tmp="${TMPDIR:-/tmp}/google-roots.pem.$$"
if wget -q "https://pki.goog/roots.pem" -O "$roots_pem_tmp"; then
	mv "$roots_pem_tmp" ~/secrets/google-roots.pem
	echo_ok "google-roots.pem updated."
else
	rm -f "$roots_pem_tmp"
	OSError "Failed to download roots.pem. The existing file is kept."
fi
unset roots_pem_tmp

echo_info "FINISHED!"

