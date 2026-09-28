#!/bin/sh

#===============================================================================
#
#          FILE:  battery_info.sh
#         USAGE:  ./battery_info.sh [tmux|zjstatus]
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#   DESCRIPTION:  Use for status bars (zellij/zjstatus, tmux, screen)
#
#===============================================================================

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
	echo "Usage: $(basename "$0") [tmux|zjstatus]"
	echo "Displays battery status information, suitable for use in status bars."
	echo ""
	echo "Arguments (optional):"
	echo "  tmux     - Format output for tmux status bar (colored, with #[default] reset)."
	echo "  zjstatus - Format output for zjstatus (colored; needs rendermode \"dynamic\")."
	echo "  If no argument is given, plain text is printed (screen, or by hand)."
	echo ""
	echo "The gauge is drawn with Nerd Font battery glyphs where a Nerd Font is"
	echo "available, and with block characters (e.g. 55% ▇▇▁▁) otherwise."
	echo "Set HAVE_NERDFONT=1 (or 0) to override the built-in host list."
	exit 0
fi

STYLE="$1"

# ----- 段階表示の色
# 20% 以下が赤、80% 以上が緑、その間はオレンジを経由して線形に混ぜる。
# 赤とオレンジは cpuload.sh の負荷色と同じ値で、ステータスバー全体の色を揃える。
COLOR_LOW="215 66 66"    # #D74242
COLOR_MID="215 160 66"   # #D7A042
COLOR_HIGH="95 215 95"   # #5FD75F
COLOR_PLAIN="#eaf0f6"    # AC 駆動など、残量で警告する必要がないとき

# ----- POSIX sh には配列がないので、位置パラメータを引く小道具で代用する
# nth <0 始まりの番号> <要素>...
nth() {
	_n=$1
	shift
	eval "printf '%s' \"\${$(( _n + 1 ))}\""
}

# lerp_color <r1> <g1> <b1> <r2> <g2> <b2> <t> <tmax>
# 色1 から色2 へ t/tmax だけ進んだ色を #RRGGBB で返す。
lerp_color() {
	printf '#%02X%02X%02X' \
		$(( $1 + ($4 - $1) * $7 / $8 )) \
		$(( $2 + ($5 - $2) * $7 / $8 )) \
		$(( $3 + ($6 - $3) * $7 / $8 ))
}

# level_color <残量%>
# COLOR_* は "r g b" の 3 語なので、lerp_color へ渡すときの分割は意図したもの。
# shellcheck disable=SC2086
level_color() {
	_pct=$1
	[ "$_pct" -lt 20 ] && _pct=20
	[ "$_pct" -gt 80 ] && _pct=80
	if [ "$_pct" -le 50 ]; then
		lerp_color $COLOR_LOW $COLOR_MID $(( _pct - 20 )) 30
	else
		lerp_color $COLOR_MID $COLOR_HIGH $(( _pct - 50 )) 30
	fi
}

# ----- Nerd Font のバッテリーグリフを使ってよいか
# グリフを持っているのは描画している端末エミュレータなので、ssh 先でも手元の
# 端末が Nerd Font なら使える。つまりホスト名だけでは決めきれない。HAVE_NERDFONT
# を立てておけばそちらが優先で、未設定のときだけ既知のホストで有効にする。
have_nerdfont() {
	if [ -n "$HAVE_NERDFONT" ]; then
		[ "$HAVE_NERDFONT" != "0" ]
		return
	fi
	case "$(hostname)" in
		aluminum|aluminum.local) return 0 ;;
		*) return 1 ;;
	esac
}

# ----- 残量計
# nerd_glyph <残量%> [charging]
# 10% 刻みの 11 段階。放電中と充電中で字形が分かれる (nf-md-battery_*)。
nerd_glyph() {
	_idx=$(( ($1 + 5) / 10 ))
	if [ "$2" = "charging" ]; then
		nth "$_idx" 󰢜 󰢜 󰂆 󰂇 󰂈 󰢝 󰂉 󰢞 󰂊 󰂋 󰂅
	else
		nth "$_idx" 󰂎 󰁺 󰁻 󰁼 󰁽 󰁾 󰁿 󰂀 󰂁 󰂂 󰁹
	fi
}

# block_bar <残量%>
# 4 セル × 3 段 = 12 ユニットを左から詰める。▇▇▇▇ から ▁▁▁▁ まで 13 段階で、
# 幅はちょうど 4 桁 ("[🔋]" が占めていたぶん) に収まる。
block_bar() {
	_units=$(( ($1 * 12 + 50) / 100 ))
	_cell=0
	while [ "$_cell" -lt 4 ]; do
		_fill=$(( _units - 3 * _cell ))
		[ "$_fill" -lt 0 ] && _fill=0
		[ "$_fill" -gt 3 ] && _fill=3
		nth "$_fill" ▁ ▃ ▅ ▇
		_cell=$(( _cell + 1 ))
	done
}

# ----- 出力
# render <本文> [色]
# 色を渡さなければ、その状態では残量を気にしなくてよいという意味。
render() {
	case "$STYLE" in
		zjstatus)
			printf '#[fg=%s]%s\n' "${2:-$COLOR_PLAIN}" "$1"
			;;
		tmux)
			if [ -n "$2" ]; then
				printf '#[fg=%s]%s#[default]\n' "$2" "$1"
			else
				printf '%s\n' "$1"
			fi
			;;
		*)
			printf '%s\n' "$1"
			;;
	esac
}

# ----- 状態の取得
# STATE: none (電池なし) | full (満充電で AC) | charging | discharging
# BATPER: 残量 (%)。STATE が none のときは空。
STATE=""
BATPER=""

if command -v ioreg > /dev/null 2>&1; then
	# macOS
	BATRAW=$(ioreg -c AppleSmartBattery -r)
	# Read the value after `"Key" = ` instead of a fixed field number: ioreg indents
	# the properties with the registry tree (`|   "MaxCapacity" = 100`), and how many
	# of those prefix columns there are depends on how deep the node sits, which moved
	# by one on macOS 27 and shifted every $3 onto the `=` sign (division by zero).
	# The space around `=` also keeps this from matching the packed copies inside the
	# "BatteryData" dictionary (`"MaxCapacity"=100`).
	battery_prop() {
		printf '%s\n' "$BATRAW" | awk -v key="\"$1\" = " '
			(pos = index($0, key)) {
				value = substr($0, pos + length(key))
				sub(/[[:space:]]+$/, "", value)
				print value
				exit
			}'
	}
	MAXCAP=$(battery_prop MaxCapacity)
	CURCAP=$(battery_prop CurrentCapacity)
	BATTERY=$(battery_prop BatteryInstalled)
	FULL=$(battery_prop FullyCharged)
	AC=$(battery_prop ExternalConnected)
	BATPER=$(awk -v cur="$CURCAP" -v max="$MAXCAP" \
		'BEGIN { if (max + 0 > 0) printf("%.0f", cur / max * 100) }')
	if [ "$BATTERY" = "No" ] || [ -z "$BATPER" ]; then
		# Desktop PC, no battery (or the charge could not be read at all)
		STATE="none"
	elif [ "$FULL" = "Yes" ] && [ "$AC" = "Yes" ]; then
		STATE="full"
	elif [ "$AC" = "Yes" ]; then
		STATE="charging"
	else
		STATE="discharging"
	fi
elif [ -d /sys/class/power_supply ]; then
	# Linux
	BAT_PATH=$(find /sys/class/power_supply/ -name 'BAT*' | head -n 1)
	# Check if there is a battery
	if [ -n "$BAT_PATH" ] && [ -e "$BAT_PATH/capacity" ]; then
		BATPER=$(cat "$BAT_PATH/capacity")
		case "$(cat "$BAT_PATH/status")" in
			Charging) STATE="charging" ;;
			Full)     STATE="full" ;;
			*)        STATE="discharging" ;;
		esac
	else
		# Desktop PC, no battery
		STATE="none"
	fi
fi

case "$STATE" in
	none|full)
		# AC で動いていて、残量を気にする理由がない状態。段階表示の出番はない。
		if have_nerdfont; then
			render "󰚥"
		else
			render "[🔌]"
		fi
		;;
	charging|discharging)
		# 色は残量、字形は充電中かどうかを表す (直交させて読み分ける)。
		if have_nerdfont; then
			GAUGE=$(nerd_glyph "$BATPER" "$STATE")
		elif [ "$STATE" = "charging" ]; then
			GAUGE="⚡️$(block_bar "$BATPER")"
		else
			GAUGE=$(block_bar "$BATPER")
		fi
		render "${BATPER}% ${GAUGE}" "$(level_color "$BATPER")"
		;;
esac
