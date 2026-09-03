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

# Directories this script empties or prunes. Their combined shrinkage is the
# only honest measure of what a run achieved: df cannot show it, because APFS
# keeps local snapshots (hourly, a rolling 24h window) that hold every freed
# block referenced until 'tmutil thinlocalsnapshots' runs. Reporting df here
# used to print an unchanged number even after tens of GB had been removed.
# Paths that do not exist are skipped, so caches of tools that are not
# installed can be listed safely.
typeset -ga CLEAN_TARGETS=(
	# Xcode / CoreSimulator
	~/Library/Developer/Xcode/DerivedData
	"$HOME/Library/Developer/Xcode/iOS DeviceSupport"
	~/Library/Developer/Xcode/Archives
	~/Library/Caches/com.apple.dt.Xcode
	~/Library/Developer/CoreSimulator/Caches
	~/Library/Developer/CoreSimulator/Devices
	# Homebrew ('brew autoremove' prunes the Cellar itself, not just the cache)
	~/Library/Caches/Homebrew
	/opt/homebrew/Cellar
	# Node.js / JavaScript
	~/.npm
	~/Library/Caches/node-gyp
	~/Library/pnpm/store
	~/.bun/install/cache
	~/Library/Caches/ms-playwright
	~/Library/Caches/Cypress
	# Python
	~/Library/Caches/pip
	~/.cache/uv
	# Rust (registry cache only, toolchains live elsewhere and are kept)
	~/.cargo/registry
	~/.cargo/git
	# Go
	~/go/pkg/mod
)

# Combined size of $CLEAN_TARGETS in KiB. du counts allocated blocks, which is
# what actually returns to the volume, rather than the apparent size.
clean_targets_kb(){
	# Not named 'path': zsh ties $path to $PATH, so assigning a directory to it
	# would wipe the command search path and du would not be found.
	local total=0 target size
	for target in $CLEAN_TARGETS; do
		[[ -e $target ]] || continue
		# du prints "<kb>\t<path>"; strip the path in the shell rather than
		# spawning cut for every entry.
		size=$(du -sk -- $target 2>/dev/null)
		size=${size%%[[:space:]]*}
		[[ $size == <-> ]] && (( total += size ))
	done
	print -r -- $total
}

# 1536 -> "1.5M". One decimal, so a few hundred MiB does not read as "0G".
format_kb(){
	local -i kb=$1
	local sign=""
	(( kb < 0 )) && { sign="-"; kb=$(( -kb )); }
	if   (( kb >= 1048576 )); then printf '%s%.1fG' "$sign" $(( kb / 1048576.0 ))
	elif (( kb >= 1024 ));    then printf '%s%.1fM' "$sign" $(( kb / 1024.0 ))
	else                           printf '%s%dK'   "$sign" $kb
	fi
}

OSNotify "Cleaning Caches..."
cachebefore=$(clean_targets_kb)
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

cacheafter=$(clean_targets_kb)
freed=$(( cachebefore - cacheafter ))
if (( freed >= 0 )); then
	OSNotify "Cleaned. Caches: $(format_kb $cachebefore) -> $(format_kb $cacheafter) (freed $(format_kb $freed))"
else
	# A toolchain repopulating its cache mid-run (a background npm/uv process,
	# say) is the usual cause, and is worth seeing rather than hiding as 0.
	OSNotify "Cleaned. Caches: $(format_kb $cachebefore) -> $(format_kb $cacheafter) (grew by $(format_kb $(( -freed ))))"
fi
