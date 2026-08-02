#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  macos_clean_caches.sh
#         USAGE:  ./macos_clean_caches.sh
#   DESCRIPTION:  Reclaim disk space by emptying the caches of the development
#                 toolchains, and report how much was freed.
#  REQUIREMENTS:  Xcode, brew, npm/pnpm/bun, pip3/uv, cargo-cache, go
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

OSNotify "Cleaning Caches..."
hdfreebefore=$(df -h / | awk 'NR==2 {print $4}')
cd ~

# Glob qualifier (ND) on the rm patterns below:
#   N ... nullglob. Without it zsh aborts the rm with "no matches found"
#         whenever the directory is already empty or missing.
#   D ... glob dots. Also match .DS_Store and friends ('.' and '..' are
#         never included, so this is safe to pass to rm -rf).
# Xcode
rm -rf ~/Library/Developer/Xcode/DerivedData/*(ND)
rm -rf ~/Library/Developer/Xcode/iOS\ DeviceSupport/*(ND)
rm -rf ~/Library/Developer/Xcode/Archives/*(ND)
rm -rf ~/Library/Caches/com.apple.dt.Xcode/*(ND)
rm -rf ~/Library/Developer/CoreSimulator/Caches/dyld/*(ND)
xcrun simctl delete unavailable
# Homebrew
brew autoremove
brew cleanup -s --prune=1
# Node.js / JavaScript
npm cache clean --force
rm -rf ~/Library/Caches/node-gyp
pnpm store prune
bun pm cache rm
# --yes: never stop for npx's "install playwright?" prompt.
# --all: 'uninstall' takes no positional argument; the flag is what
#        removes browsers of every Playwright installation.
npx --yes playwright uninstall --all
rm -rf ~/Library/Caches/Cypress/*(ND)
# Python
pip3 cache purge
uv cache clean
# Rust (registry cache only, keep toolchains)
cargo cache -a
# Go
go clean -modcache

hdfreeafter=$(df -h / | awk 'NR==2 {print $4}')
OSNotify "Cleaned. Free space: $hdfreebefore -> $hdfreeafter"
