#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  generic_zjstatus_update.sh
#         USAGE:  ./generic_zjstatus_update.sh
#   DESCRIPTION:  Notify when the zjstatus plugin cached by zellij is older than
#                 the latest release.
#
#                 layouts/default.kdl loads zjstatus from the "latest/download"
#                 URL, but zellij names the downloaded wasm after a hash of that
#                 URL and skips the download whenever the file already exists
#                 (zellij-utils/src/downloader.rs). Since the URL never changes,
#                 the very first version ever fetched is used forever - it once
#                 kept a January build running until August, which broke the
#                 clock in the status bar (zjstatus #253 was the fix).
#                 Deleting the cached file is what actually triggers an update,
#                 so detect the staleness and tell the user to do that.
#  REQUIREMENTS:  curl, shasum
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

ZJSTATUS_REPO="dj95/zjstatus"
ZJSTATUS_ASSET_URL="https://github.com/${ZJSTATUS_REPO}/releases/latest/download/zjstatus.wasm"
# Remembers "<tag> <sha256 of that tag's asset>" so that the 4MB asset is only
# downloaded again once a new release actually shows up.
STATE_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/zjstatus_release"

if [[ "$OSTYPE" = darwin* ]]; then
	ZELLIJ_CACHE_DIR="$HOME/Library/Caches/org.Zellij-Contributors.Zellij"
else
	ZELLIJ_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/zellij"
fi

# zellij stores every downloaded plugin flat in the cache root under an opaque
# hash of its URL, so identify ours by content rather than by name. (N.L+1048576)
# keeps only regular files above 1MB, i.e. the wasm blobs and not permissions.kdl.
find_cached_zjstatus(){
	local candidate
	[[ -d "$ZELLIJ_CACHE_DIR" ]] || return 0
	for candidate in "$ZELLIJ_CACHE_DIR"/*(N.L+1048576); do
		grep -qa "zjstatus" "$candidate" && print -r -- "$candidate"
	done
}

sha256_of(){
	shasum -a 256 "$1" | cut -d' ' -f1
}

# The sha256 of the asset the latest release publishes, without re-downloading
# it on every maintenance run.
latest_asset_sha256(){
	local tag json state_tag state_sha tmp sha

	json=$(curl -sfL "https://api.github.com/repos/${ZJSTATUS_REPO}/releases/latest") || return 1
	tag=$(print -r -- "$json" | grep -o '"tag_name": *"[^"]*"' | head -n 1 | cut -d'"' -f4)
	[[ -n "$tag" ]] || return 1

	if [[ -r "$STATE_FILE" ]]; then
		read -r state_tag state_sha < "$STATE_FILE"
		if [[ "$state_tag" = "$tag" && -n "$state_sha" ]]; then
			print -r -- "$tag $state_sha"
			return 0
		fi
	fi

	tmp="${TMPDIR:-/tmp}/zjstatus.wasm.$$"
	if ! curl -sfL "$ZJSTATUS_ASSET_URL" -o "$tmp"; then
		rm -f "$tmp"
		return 1
	fi
	sha=$(sha256_of "$tmp")
	rm -f "$tmp"

	mkdir -p "${STATE_FILE:h}" && print -r -- "$tag $sha" > "$STATE_FILE"
	print -r -- "$tag $sha"
}

echo_info "zjstatus plugin cache check"

typeset -a cached
cached=("${(@f)$(find_cached_zjstatus)}")
cached=("${(@)cached:#}")

if (( ${#cached} == 0 )); then
	echo_ok "No zjstatus wasm cached; zellij will fetch the latest one on its next start."
	exit 0
fi

if ! latest=$(latest_asset_sha256); then
	OSError "Could not check the latest zjstatus release."
	exit 1
fi
latest_tag="${latest%% *}"
latest_sha="${latest##* }"

typeset -a stale
for wasm in "${cached[@]}"; do
	[[ "$(sha256_of "$wasm")" = "$latest_sha" ]] || stale+=("$wasm")
done

if (( ${#stale} == 0 )); then
	echo_ok "zjstatus cache is up to date ($latest_tag)."
	exit 0
fi

echo_info "Remove the file(s) below and restart every zellij session to pick up $latest_tag:"
printf '  rm %s\n' "${stale[@]}"
OSNotify "zjstatus $latest_tag is out; the cached plugin is older. See the maintain log for how to update."
