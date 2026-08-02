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
brew update || count_failure "brew update failed."
brew outdated   # informational only
# A cask that cannot be upgraded makes this exit non-zero while the rest of the
# upgrade still succeeds, so keep going and report at the end.
brew upgrade || count_failure "brew upgrade failed. Check the log for which formula or cask."
brew bundle dump -f --file ${DOTFILES}/Brewfile || count_failure "brew bundle dump failed."

routine_exit_status