#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  generic_tinytex_update.sh
#         USAGE:  ./generic_tinytex_update.sh
#   DESCRIPTION:  Update TinyTeX (tlmgr itself and every installed package).
#  REQUIREMENTS:  TinyTeX in ~/Library/TinyTeX (macOS) or ~/.TinyTeX (Linux)
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: ${0:t} [--help]"
    echo "Update TinyTeX with 'tlmgr update --self --all'. Only the packages that"
    echo "changed are downloaded, unlike MacTeX, which is replaced as a whole."
    echo "Hosts without TinyTeX are skipped."
    echo ""
    echo "Requires TinyTeX. Normally started by maintain.sh."
    exit 0
fi

# maintain.sh runs without .zshrc, so tlmgr is not on PATH: look in TinyTeX's
# own install locations instead. (N) drops the pattern when nothing matches.
tlmgr_candidates=($HOME/Library/TinyTeX/bin/*/tlmgr(N) $HOME/.TinyTeX/bin/*/tlmgr(N))
if (( ${#tlmgr_candidates} == 0 )); then
    echo_warn "TinyTeX is not installed on this host: skipped."
    exit 0
fi
tlmgr_path="${tlmgr_candidates[1]}"

echo_info "Updating TinyTeX ($tlmgr_path)..."
# tlmgr runs updmap / fmtutil from its own bin directory, so put it first.
PATH="${tlmgr_path:h}:$PATH" "$tlmgr_path" update --self --all
tlmgr_status=$?
(( tlmgr_status == 0 )) || count_failure "TinyTeX update failed (exit $tlmgr_status)."

routine_exit_status
