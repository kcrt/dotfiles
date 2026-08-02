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

# 3725 -> "62m5s", 42 -> "42s"
format_duration(){
	local sec=$1
	if (( sec >= 60 )); then
		print -r -- "$(( sec / 60 ))m$(( sec % 60 ))s"
	else
		print -r -- "${sec}s"
	fi
}

typeset -ga FAILED_STEPS=()
typeset -gi STEP_COUNT=0

# run_step "Human readable name" command [args...]
# A full run takes hours and scrolls thousands of lines past, so time every
# step and remember its failure instead of letting it disappear in the log.
run_step(){
	local name="$1"; shift
	local start=$SECONDS rc=0
	(( ++STEP_COUNT ))
	echo_info "==== $name ===="
	"$@" || rc=$?
	local elapsed=$(format_duration $(( SECONDS - start )))
	if (( rc == 0 )); then
		echo_ok "---- $name ($elapsed)"
	else
		FAILED_STEPS+=("$name (exit $rc)")
		OSError "$name failed after $elapsed (exit $rc)"
	fi
	return $rc
}

# Report everything that went wrong in one place, and leave a non-zero exit
# status behind for whoever (launchd, a future cron job) started us.
finish(){
	local total=$(format_duration $SECONDS)
	if (( ${#FAILED_STEPS} == 0 )); then
		echo_ok "==== FINISHED! $STEP_COUNT steps in $total ===="
		OSNotify "All $STEP_COUNT steps finished in $total."
		exit 0
	fi
	echo_error "==== ${#FAILED_STEPS} of $STEP_COUNT step(s) failed (total $total) ===="
	printf '  - %s\n' "${FAILED_STEPS[@]}"
	OSError "Failed: ${(j:, :)FAILED_STEPS}"
	exit 1
}

case $HOST in
	aluminum.local)
		# Almost everything below needs the NAS at home, so its reachability is
		# what "am I at home?" actually means here.
		if ! ping -c 1 qnap.local &> /dev/null; then
			OSError "qnap.local is not reachable. Please execute this script at home."
			exit 1
		fi

		run_step "Homebrew upgrade"  run_routine macos_brew_upgrade.sh
		run_step "Virus scan"        run_routine generic_clamscan_update_and_scan.sh
		# Before sending server, find Cargo.toml and execute cargo clean
		run_step "Rust project clean" run_routine generic_cargo_clean.sh
		run_step "QNAP file list"    run_routine aluminum_qnap_filelist.sh
		run_step "Backup and sync"   run_routine aluminum_backup.sh
		run_step "Recording"         run_routine aluminum_recording.sh
		run_step "KeePass backup"    run_routine macos_keepass_backup.sh
		run_step "Clean caches"      run_routine macos_clean_caches.sh

		# echo_info "==== joplin ===="
		# joplin sync

		# echo_info "==== listing data on server ===="
		# gsutil ls -R gs://backup.kcrt.net/ | tee ~/gs_backup.txt
		;;
	*)
		echo_error "$HOST is unknown host!"
esac

run_step "CLI tools update" run_routine generic_cli_tools_update.sh
run_step "R packages"       run_routine generic_r_install_packages.sh

finish

