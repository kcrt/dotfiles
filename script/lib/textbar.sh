# textbar.sh — a fixed-width text gauge for status bars
# Usage: source this file, then call text_bar <done> <total> <cells>
# POSIX sh; no set -e / set -u here, the caller controls its own options.
#
# The cells follow lib/progressbar.py, so a status bar and the terminal line
# drawn by ffmpeg-convert.py read alike: full blocks, the fractional cell as a
# partial block (1/8 steps), the rest as light shade. Every glyph is one cell
# wide (East Asian Width = Ambiguous, which terminals and unicode-width both
# treat as narrow), so the gauge is exactly <cells> columns.
#
#   text_bar 52 100 4   ->  ██▏░
#   text_bar 2 12 6     ->  █░░░░░

# text_bar <done> <total> <cells>
# A total of 0 or less draws an empty gauge rather than dividing by zero; a done
# past the total stays full.
text_bar() {
	_tb_done=$1
	_tb_total=$2
	_tb_cells=$3
	if [ "$_tb_total" -le 0 ]; then
		_tb_eighths=0
	else
		[ "$_tb_done" -lt 0 ] && _tb_done=0
		[ "$_tb_done" -gt "$_tb_total" ] && _tb_done=$_tb_total
		_tb_eighths=$(( _tb_done * _tb_cells * 8 / _tb_total ))
	fi
	_tb_index=0
	while [ "$_tb_index" -lt "$_tb_cells" ]; do
		_tb_fill=$(( _tb_eighths - _tb_index * 8 ))
		if [ "$_tb_fill" -ge 8 ]; then
			printf '█'
		elif [ "$_tb_fill" -le 0 ]; then
			printf '░'
		else
			case "$_tb_fill" in
				1) printf '▏' ;;
				2) printf '▎' ;;
				3) printf '▍' ;;
				4) printf '▌' ;;
				5) printf '▋' ;;
				6) printf '▊' ;;
				7) printf '▉' ;;
			esac
		fi
		_tb_index=$(( _tb_index + 1 ))
	done
}
