#!/usr/bin/env zsh

skip_sixel=0
for arg in "$@"; do
    case "$arg" in
        -h|--help)
            echo "Usage: $(basename "$0") [--skip-sixel]"
            echo "Demonstrates various terminal escape sequences, including:"
            echo "  - Text styles (bold / dim / italic / underline / blink / rapid blink / reverse / conceal / strikethrough / overline)"
            echo "  - Extended underlines (double / curly / dotted / dashed, with indexed and RGB underline colors)"
            echo "  - Superscript / subscript"
            echo "  - Ideogram attributes (圏点 / 傍線)"
            echo "  - SGR sub-parameter syntax (colon vs semicolon)"
            echo "  - 4-bit colors (16 colors)"
            echo "  - 8-bit colors (256 colors)"
            echo "  - 24-bit colors (true color)"
            echo "  - Character width (ASCII / full-width / CJK / emoji / combining / Nerd Font glyphs)"
            echo "  - Double-width / double-height lines (DECDWL / DECDHL)"
            echo "  - DEC Special Graphics line-drawing charset"
            echo "  - Sixel graphics (skip with --skip-sixel)"
            echo "  - Hyperlinks (OSC 8)"
            echo "  - Window title setting (OSC 0)"
            echo "  - iTerm2 notifications (OSC 9), if applicable."
            echo ""
            echo "Options:"
            echo "  --skip-sixel   Skip the Sixel section (it garbles on terminals without Sixel support)."
            echo ""
            echo "Also prints TERM, SHELL, and TERM_PROGRAM environment variables."
            exit 0
            ;;
        --skip-sixel)
            skip_sixel=1
            ;;
        *)
            echo "Unknown option: $arg" >&2
            echo "Try '$(basename "$0") --help'." >&2
            exit 1
            ;;
    esac
done

echo "TERM: $TERM"
echo "SHELL: $SHELL"

# iTerm2: TERM_PROGRAM=iTerm.app
# vscode: TERM_PROGRAM=vscode
# Terminal.app: TERM_PROGRAM=Apple_Terminal
# tmux: TERM_PROGRAM=tmux
# screen: screen doesn't set TERM_PROGRAM
echo "TERM_PROGRAM: $TERM_PROGRAM"
echo ""


# ----- Text Styles -----
# ␛[(CSI) n m  —  0 = reset
# 1 bold / 2 dim / 3 italic / 4 underline / 5 blink / 6 rapid blink / 7 reverse
# 8 conceal / 9 strikethrough / 53 overline
echo "== Text styles =="
echo "\e[1mbold\e[0m"
echo "\e[2mdim\e[0m"
echo "\e[3mitalic\e[0m"
echo "\e[4munderline\e[0m"
echo "\e[5mblink\e[0m"
echo "\e[6mrapid blink\e[0m  <- spec says faster than 5; nearly every terminal just aliases it to 5"
echo "\e[7mreverse\e[0m"
echo "\e[8mconceal\e[0m  <- the word 'conceal' should be invisible"
echo "\e[9mstrikethrough\e[0m"
echo "\e[53moverline\e[0m"
echo ""


# ----- Extended Underlines -----
# ␛[4:_n_m  n = 2 double, 3 curly, 4 dotted, 5 dashed (sub-parameter form)
# Underline color: ␛[58:5:_n_m (256-color palette) or ␛[58:2::_r_:_g_:_b_m (true color)
# ␛[59m restores the default underline color without touching anything else.
echo "== Extended underlines =="
echo "\e[4:2mdouble\e[0m"
echo "\e[4:3mcurly\e[0m"
echo "\e[4:4mdotted\e[0m"
echo "\e[4:5mdashed\e[0m"
echo "\e[4:3m\e[58:2::255:0:0mcolored curly, true color (58:2::255:0:0)\e[0m"
echo "\e[4:3m\e[58:5:33mcolored curly, palette index (58:5:33)\e[0m"
printf "underline color palette (58:5:n): "
for color in 1 2 3 4 5 6 9 10 11 12 13 14; do
    printf "\e[4:3m\e[58:5:%sm %2s \e[0m" "$color" "$color"
done
echo ""
echo "\e[4mdefault, \e[58:5:196mred (58:5:196), \e[59mdefault again (59)\e[0m"
echo ""


# ----- Superscript / Subscript -----
# ␛[73m superscript / ␛[74m subscript / ␛[75m neither
echo "== Superscript / subscript (SGR 73 / 74, reset 75) =="
echo "E=mc\e[73m2\e[75m       <- the 2 should be raised"
echo "H\e[74m2\e[75mO          <- the 2 should be lowered"
echo ""


# ----- Ideogram Attributes -----
# ␛[60m-␛[64m mark CJK text; ␛[65m cancels them.
# In vertical writing these are side lines; horizontally most terminals would
# draw them as under/overlines. Support is rare, so plain text is the norm.
echo "== Ideogram attributes (傍線・圏点, SGR 60-64, reset 65) =="
echo "\e[60m日本語テキスト\e[65m  60: 右傍線 (underline / right side line)"
echo "\e[61m日本語テキスト\e[65m  61: 右二重傍線 (double underline / right side)"
echo "\e[62m日本語テキスト\e[65m  62: 左傍線 (overline / left side line)"
echo "\e[63m日本語テキスト\e[65m  63: 左二重傍線 (double overline / left side)"
echo "\e[64m日本語テキスト\e[65m  64: 圏点 (stress marking)"
echo ""


# ----- SGR Sub-Parameter Syntax -----
# ITU T.416 / ECMA-48 give 4, 38, 48 and 58 *sub-parameters*, separated by ':'.
# The ';' spelling is a misreading of the spec that became the de-facto
# standard, and some terminals understand only that one: macOS Terminal.app is
# semicolon-only, so every ':' sample below stays plain there. That is why the
# 8-bit and 24-bit sections use ';' — otherwise those grids would vanish
# entirely on such terminals instead of just failing this one check.
# For true color T.416 also puts a color space id between the 2 and the r,
# normally left empty — hence the doubled colon in '38:2::r:g:b'. Terminals
# that reject the empty field may still accept the 5-field '38:2:r:g:b'.
echo "== SGR sub-parameter syntax (colon vs semicolon) =="
echo "8-bit   \e[38;5;196msemicolon 38;5;196\e[0m   \e[38:5:196mcolon 38:5:196\e[0m"
echo "24-bit  \e[38;2;255;128;0msemicolon 38;2;r;g;b\e[0m   \e[38:2::255:128:0mcolon 38:2::r:g:b\e[0m   \e[38:2:255:128:0mcolon 38:2:r:g:b\e[0m"
echo "The extended underlines above (4:3, 58:...) are colon-only by design:"
echo "they have no semicolon spelling, so a semicolon-only terminal cannot"
echo "render them at all."
echo ""


# ----- 4-bit Color (16 colors) -----
# 30-37 and 90-97 are foreground colors
# 40-47 and 100-107 are background colors
echo "== 4-bit color (16 colors) =="
echo "\e[40m 0 \e[41m 1 \e[42m 2 \e[43m 3 \e[44m 4 \e[45m 5 \e[46m 6 \e[47m 7 "
echo "\e[100m*0*\e[101m*1*\e[102m*2*\e[103m*3*\e[104m*4*\e[105m*5*\e[106m*6*\e[107m*7*\e[0m"
echo ""


# ----- 8-bit Color (256 colors) -----
# Foreground: ␛[38;5;<n>m   Background: ␛[48;5;<n>m
# Semicolon form on purpose: it is the widest-supported spelling, so this grid
# renders everywhere. See the sub-parameter syntax section above for the ':'
# form and why it is not used here.
# Original is: https://tools.paco.bg/14/
echo "== 8-bit color (256 colors) =="
for fgbg in 38 48 ; do # Foreground / Background
    for color in {0..255} ; do # Colors
        # Display the color
        printf "\e[${fgbg};5;%sm %3s \e[0m" "$color" "$color"
        # Display 18 colors per line
        if [ $(((color + 1) % 18)) = 4 ] ; then
            echo # New line
        fi
    done
    echo # New line
done
echo ""


# ----- 24-bit Color (true color) -----
# Foreground: ␛[38;2;<r>;<g>;<b>m   Background: ␛[48;2;<r>;<g>;<b>m
# <r> <g> <b> range from 0 to 255 inclusive.
# Semicolon form on purpose, same reason as the 8-bit section above.
# Originally taken from iTerm2 https://github.com/gnachman/iTerm2/blob/master/tests/24-bit-color.sh
echo "== 24-bit color (true color) =="

setBackgroundColor() {
    printf '\x1b[48;2;%s;%s;%sm' "$1" "$2" "$3"
}

resetOutput() {
    printf '\x1b[0m\n'
}

# Gives a color $1/255 % along HSV.
# Echoes "$red $green $blue" as integers ranging 0-255 inclusive.
rainbowColor() {
    local h=$(($1 / 43))
    local f=$(($1 - 43 * h))
    local t=$((f * 255 / 43))
    local q=$((255 - t))

    case $h in
        0) echo "255 $t 0" ;;
        1) echo "$q 255 0" ;;
        2) echo "0 255 $t" ;;
        3) echo "0 $q 255" ;;
        4) echo "$t 0 255" ;;
        5) echo "255 0 $q" ;;
        *) echo "0 0 0" ;; # execution should never reach here
    esac
}

for channel in "r" "g" "b" "rainbow"; do
    # 64 columns per line (asc/desc alternate so the gradient stays continuous across the fold)
    for range in "0 63" "127 -1 64" "128 191" "255 -1 192"; do
        for i in $(seq ${=range}); do
            case $channel in
                r)       setBackgroundColor "$i" 0 0 ;;
                g)       setBackgroundColor 0 "$i" 0 ;;
                b)       setBackgroundColor 0 0 "$i" ;;
                rainbow) setBackgroundColor ${=$(rainbowColor "$i")} ;; # ${=...}: force word splitting (zsh)
            esac
            printf ' '
        done
        resetOutput
    done
done
echo ""


# ----- Character Width -----
# Not an escape sequence, but handy to verify glyph rendering and column width.
# Wide glyphs should each occupy 2 columns; if the closing bars misalign, the
# font/terminal is miscounting widths.
echo "== Character width =="
echo "[AB]    ASCII       (1 col each)"
echo "[ＡＢ]    full-width  (2 cols each)"
echo "[日本]    CJK         (2 cols each)"
echo "[😀🎨]    emoji       (2 cols each)"
echo "[é|e\xcc\x81]    combining   (precomposed é vs e+U+0301 — should look identical)"
echo "[]  Nerd Font / Powerline glyphs (need a patched font; tofu if unsupported)"
echo ""


# ----- Double-Width / Double-Height Lines -----
# ␛#6 DECDWL double width / ␛#3 DECDHL top half / ␛#4 DECDHL bottom half
# ␛#5 DECSWL back to normal. These are *line* attributes: they apply to the
# whole line, and the two DECDHL halves must carry identical text.
echo "== Double-width / double-height lines (DECDWL / DECDHL) =="
echo "\e#6double width (DECDWL)"
echo "\e#3double height (DECDHL)"
echo "\e#4double height (DECDHL)"
echo "\e#5normal width (DECSWL)"
echo ""


# ----- DEC Special Graphics -----
# ␛(0 maps G0 to the line-drawing charset, ␛(B maps it back to ASCII.
# lqk / x / mqj become box corners and edges without needing a patched font.
echo "== DEC Special Graphics (ESC ( 0) =="
echo "The three lines below are the plain ASCII lqqqk / x   x / mqqqj."
echo "\e(0lqqqk\e(B"
echo "\e(0x   x\e(B"
echo "\e(0mqqqj\e(B"
echo ""


# ----- Sixel Graphics -----
echo "== Sixel graphics =="
if [ "$skip_sixel" = "1" ]; then
    echo "(skipped: --skip-sixel)"
else
    sixel_logo="$HOME/dotfiles/materials/image/kcrtlogo_sixel.txt"
    if [ -f "$sixel_logo" ]; then
        cat "$sixel_logo"
    else
        echo "(skipped: $sixel_logo not found)"
    fi
fi
echo ""


# ----- Link -----
# Link start: ␛](OSC) 8 ; _param_ ; _url_ ␛\(ST)
# Link end: ␛](OSC) 8 ; ; ␛\(ST)
# _param_ could be empty, or key1=value1:key2=value2:...
echo "== Hyperlink (OSC 8) =="
echo "OSC 8 turns arbitrary text into a link. The label below is plain words,"
echo "NOT a URL, so terminals that auto-detect URLs won't linkify it on their"
echo "own: if 'kcrt profile' is clickable it opens https://profile.kcrt.net;"
echo "if it stays plain text, OSC 8 is unsupported."
echo "  link -> \e]8;;https://profile.kcrt.net\e\\kcrt profile\e]8;;\e\\"
echo ""

# ----- Window Title -----
# ␛](OSC) 0 ; _title_ ␛\(ST)
echo "\e]0;My Title\e\\"

# ----- Notify (iTerm) -----
# ␛](OSC) 9 ; _message_ ␛\(ST)
if [[ $TERM_PROGRAM == "iTerm.app" ]]; then
  echo "\e]9;Message\e\\"
fi
