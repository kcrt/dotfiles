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
        if [ $? -eq 0 ]; then
            abbrev-alias cha='nix-shell -p chawan --run cha'
        fi
    fi
fi


# === unrar (RAR archives) ===
# Homebrew disabled the `rar` cask on 2026-09-01 (fails macOS Gatekeeper check),
# so the RARLAB binaries are gone. Delegate to 7-Zip instead; the verbs
# l / x / e / t are identical, so muscle memory keeps working.
if ! command -v unrar &>/dev/null && command -v 7zz &>/dev/null; then
    unrar() { 7zz "$@" }
fi
