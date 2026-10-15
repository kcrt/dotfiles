#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  forall.sh
#         USAGE:  forall [-j N] [-x] [--title TITLE] ITEM... -- COMMAND [ARG...]
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#   DESCRIPTION:  Run COMMAND once per ITEM, reporting progress both on the
#                 terminal (one line per finished item) and in the zellij status
#                 bar (progress_info.sh --title).
#
#                   forall *.MP4 -- par2 create {}
#                   forall -j 4 *.wav -- flac {}
#
#===============================================================================

setopt NO_BG_NICE	# background jobs keep their priority (and nice() may be refused)

readonly SCRIPT_DIR="${0:A:h}"
readonly PROGRESS_INFO="$SCRIPT_DIR/progress_info.sh"
source "$SCRIPT_DIR/format_duration.sh"

# Display cells allowed for the item name shown in the status bar. Same budget
# as the transfers progress_info.sh shows on its own.
readonly STATUS_NAME_CELLS=18

# Seconds between checks for a finished job in parallel mode.
readonly POLL_SECONDS=0.2

usage() {
	cat <<-EOF
	Usage: forall [options] ITEM... -- COMMAND [ARG...]

	Run COMMAND once per ITEM. In COMMAND's arguments these are replaced:
	  {}    the item              (dir/clip.MP4)
	  {.}   without extension     (dir/clip)
	  {/}   basename              (clip.MP4)
	  {/.}  basename w/o ext.     (clip)
	  {//}  directory             (dir)
	If no argument contains a placeholder, the item is appended.

	Options:
	  -j, --parallel N  Run up to N at once (default 1). Parallel jobs get
	                    stdin from /dev/null and their output interleaves.
	  -x, --stop        Stop at the first failure (running jobs are finished).
	  --title TITLE     Status-bar title (default: 🔁COMMAND). Two runs with the
	                    same title share one entry, so give one if you run two.
	  -h, --help        Show this help.

	Progress goes to stderr; COMMAND's own output is left alone.
	Exit status: 0 if every item succeeded, 1 if any failed, 130 on Ctrl-C.

	Example: forall *.MP4 -- par2 create {}
	         forall -j 4 *.wav -- ffmpeg -i {} {.}.flac
	EOF
}

die_usage() {
	print -u2 -- "forall: $1"
	print -u2 -- "Try 'forall --help'."
	exit 2
}

# ----- Arguments
parallel=1
stop_on_error=0
title=""
items=()
while (( $# > 0 )); do
	case "$1" in
		-h|--help)     usage; exit 0 ;;
		-j|--parallel) (( $# >= 2 )) || die_usage "$1 needs a number"; parallel=$2; shift ;;
		-j*)           parallel=${1#-j} ;;
		--parallel=*)  parallel=${1#*=} ;;
		-x|--stop)     stop_on_error=1 ;;
		--title)       (( $# >= 2 )) || die_usage "--title needs a value"; title=$2; shift ;;
		--)            shift; break ;;
		*)             items+=("$1") ;;
	esac
	shift
done
command_template=("$@")

[[ $parallel == <1-> ]] || die_usage "--parallel takes a positive integer: $parallel"
(( ${#command_template} > 0 )) || die_usage "no command (put it after --)"
(( ${#items} > 0 )) || { print -u2 -- "forall: no items; nothing to do"; exit 0; }
[[ -n $title ]] || title="🔁${command_template[1]:t}"

readonly total=${#items}

# ----- Terminal output
if [[ -t 2 && -z ${NO_COLOR-} && ${TERM-} != dumb ]]; then
	readonly c_ok=$'\e[32m' c_ng=$'\e[31m' c_dim=$'\e[2m' c_reset=$'\e[0m'
else
	readonly c_ok="" c_ng="" c_dim="" c_reset=""
fi

# ----- Status bar (best effort: a status bar that cannot be updated must not
# stop the job, so every error is swallowed, as lib/statusprogress.py does)
status_report() {
	"$PROGRESS_INFO" --title "$title" "$@" </dev/null >/dev/null 2>&1
}

# truncate_cells <text> <cells> -> text no wider than <cells>, middle replaced by "…"
truncate_cells() {
	local text=$1 cells=$2
	(( ${(m)#text} <= cells )) && { print -rn -- "$text"; return; }
	local head="" tail="" i
	local -i budget=$(( cells - 1 ))
	local -i head_budget=$(( (budget + 1) / 2 )) tail_budget=$(( budget / 2 ))
	for (( i = 1; i <= ${#text}; i++ )); do
		(( ${(m)#${:-$head${text[i]}}} <= head_budget )) || break
		head+=${text[i]}
	done
	for (( i = ${#text}; i >= 1; i-- )); do
		(( ${(m)#${:-${text[i]}$tail}} <= tail_budget )) || break
		tail=${text[i]}$tail
	done
	print -rn -- "$head…$tail"
}

# ----- Running
readonly PH_ITEM='{}' PH_NOEXT='{.}' PH_BASE='{/}' PH_BASE_NOEXT='{/.}' PH_DIR='{//}'

# build_command <item> -> sets $cmd
build_command() {
	local item=$1 arg has_placeholder=0
	local base=${item:t}
	local dir=${item:h}
	cmd=()
	for arg in "${command_template[@]}"; do
		[[ $arg == *'{'(|.|/|/.|//)'}'* ]] && has_placeholder=1
		# Longest first, so "{/.}" is not eaten by "{/}" ... The patterns come
		# from variables because a "/" written inline would end the pattern.
		arg=${arg//$PH_BASE_NOEXT/${base:r}}
		arg=${arg//$PH_DIR/$dir}
		arg=${arg//$PH_BASE/$base}
		arg=${arg//$PH_NOEXT/${item:r}}
		arg=${arg//$PH_ITEM/$item}
		cmd+=("$arg")
	done
	(( has_placeholder )) || cmd+=("$item")
}

started_at=$SECONDS
finished=0
failed_items=()
typeset -A job_item job_start	# pid -> item index / start time (parallel mode)

# report_finished <index> <status> <seconds taken>
report_finished() {
	local index=$1 exit_status=$2 took=$3
	local item=${items[index]} mark eta=""
	(( finished++ ))
	if (( exit_status == 0 )); then
		mark="${c_ok}✓${c_reset}"
	else
		mark="${c_ng}✗ (exit $exit_status)${c_reset}"
		failed_items+=("$item")
	fi
	if (( finished < total )); then
		local -i elapsed=$(( SECONDS - started_at ))
		eta="  ${c_dim}経過 $(format_duration $elapsed) / 残り約 $(format_duration $(( elapsed * (total - finished) / finished )))${c_reset}"
	fi
	print -u2 -- "[${(l:${#total}:)finished}/$total] $mark $item ${c_dim}($(format_duration $took))${c_reset}$eta"
	status_report --num "$finished"
}

# Ctrl-C reaches a foreground child on its own, but background jobs of a
# non-interactive shell ignore SIGINT, so they are killed here explicitly.
interrupted() {
	(( ${#job_item} > 0 )) && kill -TERM ${(k)job_item} 2>/dev/null
	wait
	print -u2 -- "${c_ng}forall: 中断しました (完了 $finished/$total)${c_reset}"
	status_report --done
	exit 130
}
trap interrupted INT TERM

status_report --num 0 --of "$total" --pid $$

# announce_start <index>: the status bar names the item that started last
announce_start() {
	status_report --set "$(truncate_cells "${items[$1]:t}" $STATUS_NAME_CELLS)"
}

integer next=1
if (( parallel == 1 )); then
	for (( ; next <= total; next++ )); do
		build_command "${items[next]}"
		announce_start $next
		local -i t0=$SECONDS
		"${cmd[@]}"
		exit_status=$?
		# A child killed by Ctrl-C: the trap may not fire for a signal that
		# only the child acted on, so stop here as well.
		(( exit_status == 130 )) && interrupted
		report_finished $next $exit_status $(( SECONDS - t0 ))
		(( exit_status != 0 && stop_on_error )) && break
	done
else
	stop_launching=0
	while (( (next <= total && !stop_launching) || ${#job_item} > 0 )); do
		while (( next <= total && !stop_launching && ${#job_item} < parallel )); do
			build_command "${items[next]}"
			announce_start $next
			"${cmd[@]}" </dev/null &
			job_item[$!]=$next
			job_start[$!]=$SECONDS
			(( next++ ))
		done
		sleep $POLL_SECONDS
		for pid in ${(k)job_item}; do
			kill -0 $pid 2>/dev/null && continue
			wait $pid
			exit_status=$?
			report_finished ${job_item[$pid]} $exit_status $(( SECONDS - job_start[$pid] ))
			unset "job_item[$pid]" "job_start[$pid]"
			(( exit_status != 0 && stop_on_error )) && stop_launching=1
		done
	done
fi

status_report --done

# ----- Summary
skipped=$(( total - finished ))
summary="完了 $(( finished - ${#failed_items} ))/$total"
(( ${#failed_items} > 0 )) && summary+=", ${c_ng}失敗 ${#failed_items}${c_reset}"
(( skipped > 0 )) && summary+=", 未実行 $skipped"
print -u2 -- "forall: $summary  ($(format_duration $(( SECONDS - started_at ))))"
for item in "${failed_items[@]}"; do
	print -u2 -- "  ${c_ng}✗${c_reset} $item"
done
(( ${#failed_items} == 0 ))
