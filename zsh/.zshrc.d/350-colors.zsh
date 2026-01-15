#
#	350-colors.zsh
#		Host-specific terminal palette and general color configuration
#

# ----- Host-specific color configuration
# not all terminals support this
typeset -A hostconfig
# Remote server: cyan, cloud machine: yellow,
# Local main machine: blue, Local sub machine: yellow
hostconfig=(
	kcrt.net               "cyan:001111"
	rctstudy.jp            "cyan:001111"
	lithium                "yellow:001111"
	aluminum               "blue:000011"
	aluminum.local         "blue:000011"
	beryllium              "yellow:001111"
	beryllium.local        "yellow:001111"
	myubuntu               "green:000000"
	mykali                 "red:000000"
	aries                  "yellow:001111"
	aries.local            "yellow:001111"
)

# Set default values
hostcolor="magenta"
hostblack="000000"

# Check if HOST exists in hostconfig associative array
if [[ -n "${hostconfig[$HOST]}" ]]; then
	# Split the config value into color and background
	hostcolor="${hostconfig[$HOST]%%:*}"
	hostblack="${hostconfig[$HOST]#*:}"
fi

# ----- Set terminal palette
# OSC P n rr gg bb ST - Set palette color n to RGB value
set_terminal_palette() {
	[[ "$SSH_CONNECTION" != "" ]] && return 0
	[[ "$TERM" != (screen*|xterm*) ]] && return 0
	echo -n "\e]R\e\\"		# Reset
	# 16-color palette: 0-7 normal, 8-15 bright
	local palette=(
		"P0${hostblack}"  # black
		"P1FF0000"        # red
		"P200CC00"        # green
		"P3CCCC00"        # yellow
		"P461A1E5"        # blue
		"P5FF00FF"        # magenta
		"P600FFFF"        # cyan
		"P7CCCCCC"        # white
		"P8676767"        # bright black
		"P9FFAAAA"        # bright red
		"PA88FF88"        # bright green
		"PBFFFFAA"        # bright yellow
		"PC7777FF"        # bright blue
		"PDFFCCFF"        # bright magenta
		"PE88FFFF"        # bright cyan
		"PFFFFFFF"        # bright white
	)

	# Apply each color
	for color in "${palette[@]}"; do
		echo -n "\e]${color}\e\\"
	done
}
set_terminal_palette

# ----- Color configuration
autoload colors					# Enables $color[red] etc.
colors
if [[ -x dircolors ]]; then
	eval `dircolors -b`
fi
export ZLS_COLORS=$LS_COLORS
export CLICOLOR=true
