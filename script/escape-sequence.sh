#!/usr/bin/env zsh

echo "TERM: $TERM"
echo "SHELL: $SHELL"

# iTerm2: TERM_PROGRAM=iTerm.app
# vscode: TERM_PROGRAM=vscode
# Terminal.app: TERM_PROGRAM=Apple_Terminal
# tmux: TERM_PROGRAM=tmux
# screen: screen doesn't set TERM_PROGRAM
echo "TERM_PROGRAM: $TERM_PROGRAM"
echo ""


# ----- Color -----
# ␛](OSC) P n rr gg bb ␛\(ST)
# 30-37 and 90-97 are foreground colors
# 40-47 and 100-107 are background colors
echo "\e[40m 0 \e[41m 1 \e[42m 2 \e[43m 3 \e[44m 4 \e[45m 5 \e[46m 6 \e[47m 7 "
echo "\e[100m*0*\e[101m*1*\e[102m*2*\e[103m*3*\e[104m*4*\e[105m*5*\e[106m*6*\e[107m*7*\e[0m"

# ----- Link -----
# Link start: ␛](OSC) 8 ; _param_ ; _url_ ␛\(ST)
# Link end: ␛](OSC) 8 ; ; ␛\(ST)
# _param_ could be empty, or key1=value1:key2=value2:...
echo "For more information, please see \e]8;;https://profile.kcrt.net\e\\my profile\e]8;;\e\\."

# ----- Window Title -----
# ␛](OSC) 0 ; _title_ ␛\(ST)
echo "\e]0;My Title\e\\"

# ----- Notify (iTerm) -----
# ␛](OSC) 9 ; _message_ ␛\(ST)
if [[ $TERM_PROGRAM == "iTerm.app" ]]; then
  echo "\e]9;Message\e\\"
fi