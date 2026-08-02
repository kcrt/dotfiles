#!/bin/sh

#===============================================================================
#
#          FILE:  progress_info.sh
#         USAGE:  ./progress_info.sh [zjstatus|tmux]
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#   DESCRIPTION:  Summarise `progress` (Coreutils Viewer) output into a single
#                 short line for a status bar. Prints nothing when no monitored
#                 command is transferring data.
#
#===============================================================================

# Seconds `progress` samples I/O for, to compute throughput / ETA.
# Each invocation blocks for roughly this long, so keep it well below the
# polling interval of the status bar.
WAIT_DELAY=0.5

# Max width of the displayed file name, in terminal cells. Longer names lose
# their middle, so a Japanese name costs twice as many cells per character and
# therefore shows about half as many of them.
MAX_NAME_LEN=18

# Transfers whose total size is below this are ignored: `progress` also watches
# `cat`, `grep`, `sort` & co, and a status bar has no room for a 200 KB read
# that finishes before the next poll.
MIN_SIZE_BYTES=1048576		# 1 MiB

# Command -> icon. One entry per line: the icon, then the commands it covers.
# The icon replaces the command name entirely, which is what makes this fit in
# a status bar; commands absent from the table fall back to FALLBACK_ICON.
#
# Every icon here has East Asian Width = Wide, so it occupies exactly two cells
# everywhere. Keep it that way when editing: an emoji that needs U+FE0F to show
# in colour (🗜️ 🖥️ ➡️ …) is EAW=Neutral, and a terminal draws it two cells wide
# while width accounting based on unicode-width counts one, which shifts a
# right-aligned bar. Symbols outside emoji-data (U+1F5B4 HARD DISK and friends)
# are worse still: Apple Color Emoji has no glyph for them at all.
COMMAND_ICONS="
📋 cp gcp
🚚 mv gmv
💾 dd
🐱 cat
🔪 split cut
🔄 rsync
🌐 scp
📱 adb
📦 tar bsdtar
🧊 gzip bzip2 xz lzma zip 7z 7za zstd
🎁 gunzip bunzip2 unxz unlzma unzip zcat bzcat lzcat
🔍 grep fgrep egrep
🔤 sort
🔢 cksum md5sum sha1sum sha224sum sha256sum sha384sum sha512sum
🔐 gpg
🎬 ffmpeg
"

# Used for commands missing from COMMAND_ICONS, e.g. anything added via
# PROGRESS_ARGS that has no entry yet.
FALLBACK_ICON="⏳"

# The other running transfers are listed as bare icons after the headline one.
# Each costs two cells, so past this many the remainder collapses to "+N".
EXTRA_ICON_LIMIT=3

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
	echo "Usage: $(basename "$0") [zjstatus|tmux]"
	echo "Summarises running file transfers (cp, mv, dd, tar, rsync, ...) as one short line."
	echo "Prints nothing when nothing is being transferred."
	echo "Transfers smaller than ${MIN_SIZE_BYTES} bytes are ignored."
	echo ""
	echo "Arguments (optional):"
	echo "  zjstatus - Colour with zjstatus markup and prepend a ' | ' separator."
	echo "  tmux     - Colour with tmux status-bar markup."
	echo "  (none)   - Plain text."
	echo ""
	echo "Example output: 📋big.iso 52% 45MB/s 24s 🌐📦"
	echo "                (the leading icon stands for the command; the trailing"
	echo "                 icons are the other transfers running right now)"
	echo ""
	echo "Set PROGRESS_ARGS to monitor extra commands, e.g."
	echo "  export PROGRESS_ARGS=\"-a zstd -a ffmpeg\""
	exit 0
fi

command -v progress >/dev/null 2>&1 || exit 0

STYLE="$1"

# `progress -q` stays silent when nothing matches, so an empty result simply
# means "no transfer in flight".
progress -q -w -W "$WAIT_DELAY" 2>/dev/null | awk \
	-v style="$STYLE" \
	-v max_name_len="$MAX_NAME_LEN" \
	-v min_bytes="$MIN_SIZE_BYTES" \
	-v icon_table="$(printf '%s' "$COMMAND_ICONS" | tr '\n' ';')" \
	-v fallback_icon="$FALLBACK_ICON" \
	-v extra_icon_limit="$EXTRA_ICON_LIMIT" '
	# COMMAND_ICONS arrives with its rows joined by ";" because BSD awk
	# rejects a literal newline inside a -v assignment.
	BEGIN {
		# macOS awk (20200816) is byte-oriented, so multibyte characters
		# have to be walked by hand. This maps a byte back to its value;
		# sprintf("%c") on this awk emits the raw byte, not a character.
		for (b = 0; b < 256; b++)
			ord[sprintf("%c", b)] = b

		rows = split(icon_table, row, ";")
		for (r = 1; r <= rows; r++) {
			line = row[r]
			sub(/^[ \t]+/, "", line)
			sub(/[ \t]+$/, "", line)
			if (line == "")
				continue
			fields = split(line, f, /[ \t]+/)
			for (k = 2; k <= fields; k++)
				icon[f[k]] = f[1]
		}
	}

	# Header line: "[ 4183] cp /path/to/file"
	# The pid is padded to 5 columns, so field numbers shift with its width:
	# strip the bracketed pid instead of relying on $2/$3.
	/^\[ *[0-9]+\]/ {
		count++
		rest = $0
		sub(/^\[[^]]*\][ \t]*/, "", rest)		# "cp /path/to/file"
		cmd = rest
		sub(/[ \t].*$/, "", cmd)
		sub(/.*\//, "", cmd)			# /usr/local/bin/rsync -> rsync
		path = rest
		sub(/^[^ \t]+[ \t]+/, "", path)
		cmds[count] = cmd
		paths[count] = path
		details[count] = ""
		next
	}

	# Detail line: "\t52.6% (1.2 GiB / 2.3 GiB) 45.3 MiB/s remaining 0:00:24"
	count > 0 && details[count] == "" && /%/ {
		details[count] = $0
	}

	function matched(s, re,   found) {
		found = match(s, re)
		return found ? substr(s, RSTART, RLENGTH) : ""
	}

	# "1.2 GiB" -> bytes. KB and KiB are treated alike; the threshold is a
	# rough noise filter, not an accounting figure. Returns -1 if unparseable.
	function to_bytes(s,   num, unit, mult) {
		if (!match(s, "^[0-9]+(\\.[0-9]+)?"))
			return -1
		num = substr(s, RSTART, RLENGTH) + 0
		unit = toupper(substr(s, RSTART + RLENGTH))
		gsub(/[ \t]/, "", unit)
		if (unit == "" || unit == "B")	mult = 1
		else if (unit ~ /^K/)		mult = 1024
		else if (unit ~ /^M/)		mult = 1048576
		else if (unit ~ /^G/)		mult = 1073741824
		else if (unit ~ /^T/)		mult = 1099511627776
		else if (unit ~ /^P/)		mult = 1125899906842624
		else				return -1
		return num * mult
	}

	# "123.4 MiB/s" -> "123MB/s". The number keeps its binary base; only the
	# label loses the "i", because three cells of status bar are worth more
	# than the 2.4% the distinction buys. The fraction goes for the same
	# reason: nobody reads the tenths digit of a throughput that is being
	# resampled every five seconds.
	function compact_rate(s,   num, unit) {
		if (!match(s, "^[0-9]+(\\.[0-9]+)?"))
			return ""
		num = substr(s, RSTART, RLENGTH) + 0
		unit = substr(s, RSTART + RLENGTH)
		gsub(/[ \t]/, "", unit)
		sub(/iB/, "B", unit)			# MiB/s -> MB/s
		return sprintf("%d%s", num + 0.5, unit)	# +0.5 to round, not truncate
	}

	# "0:00:52" -> "52s", "0:13:23" -> "13m", "1:23:45" -> "1h23".
	# Under a minute the seconds are the only digits that carry information;
	# past a minute nobody acts on the seconds; past an hour the minutes
	# matter again, because by then the hour stops visibly changing. Every
	# form carries its own unit letter, so the value needs no brackets to
	# tell it apart from the throughput next to it.
	function compact_eta(s,   n, p, h, m, sec) {
		n = split(s, p, ":")
		if (n == 3)		{ h = p[1] + 0; m = p[2] + 0; sec = p[3] + 0 }
		else if (n == 2)	{ h = 0; m = p[1] + 0; sec = p[2] + 0 }
		else			return ""
		if (h > 0)
			return sprintf("%dh%02d", h, m)
		if (m > 0)
			return sprintf("%dm", m)
		return sprintf("%ds", sec)
	}

	# Total size of a transfer, i.e. the right-hand side of the
	# "(1.2 GiB / 2.3 GiB)" pair. Returns -1 when it is not present.
	function total_bytes(detail,   paren) {
		if (!match(detail, "\\([^)]*/[^)]*\\)"))
			return -1
		paren = substr(detail, RSTART, RLENGTH)
		sub(/^.*\/[ \t]*/, "", paren)		# "2.3 GiB)"
		sub(/\).*$/, "", paren)			# "2.3 GiB"
		return to_bytes(paren)
	}

	# Bytes in the UTF-8 character whose leading byte has value b. A stray
	# continuation byte counts as one so that malformed input still advances.
	function utf8_bytes(b) {
		if (b < 192)	return 1		# ASCII, or a stray 10xxxxxx
		if (b < 224)	return 2		# 110xxxxx
		if (b < 240)	return 3		# 1110xxxx
		return 4				# 11110xxx
	}

	# Trim to at most `cells` display columns by dropping the middle: what
	# identifies a file sits at the end, so
	# "26100.1742.240906-0331.ge_release_..._x64FRE_ja-jp.iso" is worth far
	# more as "26100.17…ja-jp.iso" than as "26100.1742.24050…". The tail is
	# filled first for that reason, and gets the odd cell.
	#
	# Every non-ASCII character is charged two cells. That is exact for the
	# kana, kanji and emoji that turn up in practice, and overcharges the
	# accented Latin that does not — which only ever makes the bar narrower
	# than planned, never wider. The ellipsis is assumed to be one cell, as
	# unicode-width also treats East Asian Ambiguous as narrow.
	function elide(s, cells,   i, n, len, chars, widths, total, budget,
			      head, tail, hw, tw, out) {
		n = 0
		total = 0
		for (i = 1; i <= length(s); i += len) {
			len = utf8_bytes(ord[substr(s, i, 1)])
			n++
			chars[n] = substr(s, i, len)
			widths[n] = (len == 1) ? 1 : 2
			total += widths[n]
		}
		if (total <= cells)
			return s

		budget = cells - 1			# the ellipsis costs one cell
		tw = 0
		for (tail = 0; tail < n; tail++) {
			if (tw + widths[n - tail] > int((budget + 1) / 2))
				break
			tw += widths[n - tail]
		}
		hw = 0
		for (head = 0; head < n - tail; head++) {
			if (hw + widths[head + 1] > budget - tw)
				break
			hw += widths[head + 1]
		}

		out = ""
		for (i = 1; i <= head; i++)
			out = out chars[i]
		out = out "…"
		for (i = n - tail + 1; i <= n; i++)
			out = out chars[i]
		return out
	}

	function shorten(s) {
		sub(/.*\//, "", s)			# basename
		return elide(s, max_name_len)
	}

	END {
		if (count == 0)
			exit

		# Drop transfers too small to be worth a status-bar slot. An entry
		# whose size cannot be read (no detail line, odd unit) is kept:
		# unknown is not the same as small.
		# Compacting in place is safe because kept <= i at every step.
		kept = 0
		for (i = 1; i <= count; i++) {
			size = details[i] == "" ? -1 : total_bytes(details[i])
			if (size >= 0 && size < min_bytes)
				continue
			kept++
			cmds[kept] = cmds[i]
			paths[kept] = paths[i]
			details[kept] = details[i]
		}
		count = kept
		if (count == 0)
			exit

		# Show the transfer with the most work left, so an already-finished
		# entry (100%, fd still open) never hides an active one.
		# NOTE: regexes are passed as strings; a /literal/ argument would be
		# evaluated as a match against $0 and collapse to 0/1.
		pick = 1
		for (i = 1; i <= count; i++) {
			# An entry without a detail line carries no numbers: deprioritise
			# it rather than let a bare "0%" win the comparison.
			done_ratio = details[i] == "" ? 101 : matched(details[i], "[0-9]+(\\.[0-9]+)?%") + 0
			if (i == 1 || done_ratio < least_done) {
				least_done = done_ratio
				pick = i
			}
		}
		detail = details[pick]

		percent = matched(detail, "[0-9]+(\\.[0-9]+)?%")
		sub(/\.[0-9]+/, "", percent)			# 52.6% -> 52%

		speed = compact_rate(matched(detail, "[0-9]+(\\.[0-9]+)? [A-Za-z]+/s"))

		eta = ""
		at = index(detail, "remaining ")
		if (at > 0) {
			eta = substr(detail, at + length("remaining "))
			sub(/^[ \t]+/, "", eta)
			sub(/[ \t].*$/, "", eta)		# keep just the timestamp
			eta = compact_eta(eta)
		}

		text = (cmds[pick] in icon ? icon[cmds[pick]] : fallback_icon)
		text = text shorten(paths[pick])
		if (percent != "")	text = text " " percent
		if (speed != "")	text = text " " speed
		if (eta != "")		text = text " " eta

		# The remaining transfers appear as bare icons instead of a count:
		# no wider than "+1" for a single one, and it says what is running
		# rather than merely how much.
		extras = ""
		shown = 0
		for (i = 1; i <= count && shown < extra_icon_limit; i++) {
			if (i == pick)
				continue
			extras = extras (cmds[i] in icon ? icon[cmds[i]] : fallback_icon)
			shown++
		}
		if (count - 1 - shown > 0)
			extras = extras "+" (count - 1 - shown)
		if (extras != "")
			text = text " " extras

		if (style == "zjstatus")
			printf("#[fg=#eaf0f6] | #[fg=#45BEC9]%s#[fg=#eaf0f6]", text)
		else if (style == "tmux")
			printf("#[fg=cyan]%s#[default]", text)
		else
			print text
	}
'
