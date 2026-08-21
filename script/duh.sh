#!/usr/bin/env zsh
#
#	duh.sh
#		`du -h` that is actually readable: sorted, with bar graph and percentages.
#
#	Plain `du -h` prints unsorted numbers that are hard to compare at a glance.
#	This wrapper measures one level only, sorts by size, and draws a bar so the
#	space hog is obvious immediately.
#
#	Available as `duh` through the script alias loop in
#	zsh/.zshrc.d/705-aliases-convenience.zsh.
#

_duh_usage() {
	print -r -- "Usage: duh [-n N] [-a] [-r] [-s] [PATH...]"
	print -r -- ""
	print -r -- "Show disk usage of one directory level, sorted with a bar graph."
	print -r -- ""
	print -r -- "  no PATH      measure the entries of the current directory"
	print -r -- "  one PATH     measure the entries of that directory"
	print -r -- "  many PATHs   measure the given paths themselves"
	print -r -- ""
	print -r -- "  -n N   show only the N largest entries (default: 20, 0 = all)"
	print -r -- "  -a     show all entries (same as -n 0)"
	print -r -- "  -r     reverse order, largest entry closest to the prompt"
	print -r -- "  -s     never expand a directory argument, measure it as a whole"
	print -r -- "  -h     show this help"
	print -r -- ""
	print -r -- "Dotfiles are included. Sizes are what du reports (disk usage,"
	print -r -- "not apparent size) and symlinks are not followed."
	print -r -- ""
	print -r -- "Colour follows the terminal; NO_COLOR disables it and"
	print -r -- "CLICOLOR_FORCE=1 keeps it through a pipe (e.g. duh | less -R)."
	print -r -- ""
	print -r -- "Example: duh -n 10 ~/Downloads"
}

_duh_human() {
	# Format a size given in KiB into 5 columns, e.g. " 1.2G" / " 999M".
	local -i kib=$1
	local -F value=$kib
	local -a units=(K M G T P)
	local -i unit=1
	while (( value >= 1024.0 && unit < ${#units} )); do
		(( value = value / 1024.0 ))
		(( unit++ ))
	done
	if (( unit == 1 )); then
		# du counts whole KiB, so decimals would only be noise at this scale.
		(( kib == 0 )) && { printf '   0B'; return }
		printf '%4dK' $kib
	elif (( value >= 100.0 )); then
		printf '%4.0f%s' $value ${units[unit]}
	else
		printf '%4.1f%s' $value ${units[unit]}
	fi
}

_duh_repeat() {
	# Echo the string $1 repeated $2 times ($2 may be zero or negative).
	local -i count=$2
	local result=''
	repeat $count; do result+=$1; done
	print -rn -- $result
}

_duh_main() {
	emulate -L zsh

	local -a opt_num opt_all opt_reverse opt_summarize opt_help
	zparseopts -D -- n:=opt_num a=opt_all r=opt_reverse s=opt_summarize \
		h=opt_help -help=opt_help || { _duh_usage >&2; return 2 }

	if (( ${#opt_help} )); then
		_duh_usage
		return 0
	fi

	# zparseopts stops at the first thing it does not know, so a leftover
	# option-looking argument is a typo rather than a path.
	if [[ -n $1 && $1 == -* && ! -e $1 ]]; then
		print -u2 -r -- "duh: unknown option: $1"
		_duh_usage >&2
		return 2
	fi

	local -i limit=20
	if (( ${#opt_num} )); then
		[[ ${opt_num[2]} == <-> ]] || {
			print -u2 -r -- "duh: -n needs a number, got: ${opt_num[2]}"
			return 2
		}
		limit=${opt_num[2]}
	fi
	(( ${#opt_all} )) && limit=0

	# Decide what to measure: entries of a directory, or the arguments themselves.
	local -a targets
	local label=$PWD
	local -i expanded=1
	if (( $# == 0 )); then
		targets=(*(ND))
	elif (( $# == 1 && ${#opt_summarize} == 0 )) && [[ -d $1 ]]; then
		targets=(${1%/}/*(ND))
		label=${1:a}
	else
		targets=("$@")
		expanded=0
	fi

	if (( ${#targets} == 0 )); then
		print -u2 -r -- "duh: nothing to measure in ${label}"
		return 1
	fi

	# du's own errors are silenced below to keep the table clean, so report
	# missing paths here instead of showing an empty result.
	local target
	for target in "${targets[@]}"; do
		[[ -e $target || -L $target ]] || {
			print -u2 -r -- "duh: no such file or directory: ${target}"
			return 1
		}
	done

	local -a sizes names
	local -i total=0
	local line
	for line in ${(f)"$(du -sk -- "${targets[@]}" 2>/dev/null | sort -k1,1nr -k2,2)"}; do
		[[ -z $line ]] && continue
		sizes+=(${line%%$'\t'*})
		names+=("${line#*$'\t'}")
		(( total += ${line%%$'\t'*} ))
	done

	if (( ${#sizes} == 0 )); then
		print -u2 -r -- "duh: could not measure anything (permission denied?)"
		return 1
	fi

	local -i shown=${#sizes}
	(( limit > 0 && limit < shown )) && shown=limit

	# Colours only when we are talking to a terminal, unless told otherwise.
	local -i use_colour=0
	if [[ -n ${CLICOLOR_FORCE:-} && ${CLICOLOR_FORCE} != 0 ]]; then
		use_colour=1
	elif [[ -n ${NO_COLOR:-} ]]; then
		use_colour=0
	elif [[ -t 1 ]]; then
		use_colour=1
	fi

	local c_reset='' c_dim='' c_dir='' c_link='' c_total=''
	local -a c_bar=('' '' '' '')
	if (( use_colour )); then
		c_reset=$'\e[0m'
		c_dim=$'\e[2m'
		c_dir=$'\e[1;34m'
		c_link=$'\e[36m'
		c_total=$'\e[1m'
		c_bar=($'\e[31m' $'\e[33m' $'\e[32m' $'\e[2;32m')
	fi

	local -i columns=${COLUMNS:-$(tput cols 2>/dev/null || print 80)}
	local -i bar_width=$(( columns - 34 ))
	(( bar_width < 8 )) && bar_width=8
	(( bar_width > 48 )) && bar_width=48

	# Sub-character resolution so small entries still show something.
	local -a eighths=('' '▏' '▎' '▍' '▌' '▋' '▊' '▉')
	local -i largest=${sizes[1]}

	local -a order=({1..$shown})
	(( ${#opt_reverse} )) && order=(${(Oa)order})

	local -i index
	for index in $order; do
		local -F share=0.0
		(( total > 0 )) && (( share = 100.0 * ${sizes[index]} / total ))

		# Integer maths with explicit rounding; zsh/mathfunc is not always loaded.
		local -i ticks=0
		(( largest > 0 )) && \
			ticks=$(( (${sizes[index]} * bar_width * 8 + largest / 2) / largest ))
		(( ticks < 1 && ${sizes[index]} > 0 )) && ticks=1
		local -i blocks=$(( ticks / 8 ))
		local -i fraction=$(( ticks % 8 ))
		local bar="$(_duh_repeat '█' $blocks)${eighths[fraction + 1]}"
		bar+="$(_duh_repeat ' ' $(( bar_width - blocks - (fraction > 0) )))"

		local colour=${c_bar[4]}
		(( share >= 25.0 )) && colour=${c_bar[1]}
		(( share >= 10.0 && share < 25.0 )) && colour=${c_bar[2]}
		(( share >= 3.0 && share < 10.0 )) && colour=${c_bar[3]}

		# Inside one directory the basename is enough; explicit arguments are
		# shown as given so paths from different places stay distinguishable.
		local name=${names[index]}
		(( expanded )) && name=${name:t}
		if [[ -L ${names[index]} ]]; then
			name="${c_link}${name}@${c_reset}"
		elif [[ -d ${names[index]} ]]; then
			name="${c_dir}${name}/${c_reset}"
		fi

		printf '%s  %s%s%s  %s%5.1f%%%s  %s\n' \
			"$(_duh_human ${sizes[index]})" \
			"$colour" "$bar" "$c_reset" \
			"$c_dim" $share "$c_reset" \
			"$name"
	done

	local scope="${#sizes} item"
	(( ${#sizes} != 1 )) && scope+='s'
	(( expanded )) && scope+=" in ${label}"

	local note=''
	(( shown < ${#sizes} )) && note=" ${c_dim}(top ${shown} of ${#sizes}, -a for all)${c_reset}"
	print -r -- "${c_dim}$(_duh_repeat '─' $(( bar_width + 22 )))${c_reset}"
	printf '%s%s  %s%s%s\n' \
		"$c_total" "$(_duh_human $total)" "$scope" "$c_reset" "$note"
}

_duh_main "$@"
