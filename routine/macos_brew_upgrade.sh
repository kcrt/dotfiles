#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  macos_brew_upgrade.sh
#         USAGE:  ./macos_brew_upgrade.sh
#   DESCRIPTION:  Update and upgrade Homebrew packages
#  REQUIREMENTS:  brew
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

OSNotify "Updating brew..."
brew update
brew outdated
brew upgrade
brew bundle dump -f --file ${DOTFILES}/Brewfile