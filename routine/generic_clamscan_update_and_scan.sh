#!/usr/bin/env zsh

source ${DOTFILES}/script/OSNotify.sh

OSNotify "Anti-virus database updating..."
freshclam

OSNotify "Scanning system. This may take a while..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    clamscan --infected --cross-fs=no --recursive ~/Downloads # ~/Documents ~/Desktop
else
    clamscan --infected --cross-fs=no --recursive "$HOME"
fi

# if command fails, pause and wait for user to press enter
if [[ $? -ne 0 ]]; then
    OSError "!!! Virus found !!!"
    echo "Please check message. Press Enter key to continue..."
    read
fi
 