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
# Claude Desktop and every Claude Code session keep a uvx MCP server alive, and
# each one holds ~/.cache/uv/.lock for its whole lifetime, so uv sits here for
# its default 300s and then gives up. Notify as soon as we know we are going to
# wait - closing Claude within the window is enough to let it through - and cap
# the wait at a minute. ('uv cache size' does not need the lock.)
if lsof ~/.cache/uv/.lock > /dev/null 2>&1; then
    OSNotify "uv cache is locked by a running uv process (Claude's MCP servers). Waiting up to 1 min; close Claude to let it through."
fi
if UV_LOCK_TIMEOUT=60 uv cache clean; then
    echo_ok "uv cache cleaned."
else
    echo_warn "uv cache left alone ($(uv cache size 2>/dev/null | awk '{printf "%.1fG", $1/1024/1024/1024}')): the lock was still held."
fi
# Rust (registry cache only, keep toolchains)
cargo cache -a
# Go
go clean -modcache

hdfreeafter=$(df -h / | awk 'NR==2 {print $4}')
OSNotify "Cleaned. Free space: $hdfreebefore -> $hdfreeafter"
