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
		run_routine generic_cargo_clean.sh

		run_routine aluminum_qnap_filelist.sh

		echo_info "==== Data back up and sync ===="
		run_routine aluminum_backup.sh

		echo_info "==== recording (if available) ===="
		run_routine aluminum_recording.sh

		echo_info "==== keepass ===="
		run_routine macos_keepass_backup.sh

		run_routine macos_clean_caches.sh

		# echo_info "==== joplin ===="
		# joplin sync

		# echo_info "==== listing data on server ===="
		# gsutil ls -R gs://backup.kcrt.net/ | tee ~/gs_backup.txt
		;;
	*)
		echo_error "$HOST is unknown host!"
esac

run_routine generic_cli_tools_update.sh

run_routine generic_r_install_packages.sh

echo_info "FINISHED!"

