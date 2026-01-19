#
# if command not found, suggest installing package
#


# === cha (chawan) ===
if ! command -v cha &>/dev/null; then
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        alias cha='echo "cha (chawan) not found. Please install with brew install chawan"'
    elif command -v nix-shell &>/dev/null; then
        # other OS with nix
        ${DOTFILES}/script/ask.sh "cha (chawan) command not found. Do you want to use it with nix?" -y
        if [ $? -eq 0 ]; then
            abbrev-alias cha='nix-shell -p chawan --run cha'
        fi
    fi
fi