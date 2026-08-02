#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  generic_cli_tools_update.sh
#         USAGE:  ./generic_cli_tools_update.sh
#   DESCRIPTION:  Keep the small command line tools current: vim plugins, the
#                 Google Cloud SDK, the GitHub Copilot extension and Google's
#                 root certificates.
#  REQUIREMENTS:  vim (vim-plug), wget; gcloud and gh are optional
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

echo_info "vim update"
# .vimrc uses vim-plug (PluginInstall is Vundle's command and does not exist).
# --sync is required so that the updates finish before vim quits.
# -es (silent ex mode) avoids redrawing a full screen of escape sequences into
# maintain.sh's log; -u is needed with it because -es skips the normal startup
# and vim-plug's commands are defined in .vimrc.
vim -es -u ~/.vimrc -c "PlugInstall --sync" -c "PlugUpdate --sync" -c "qall!" < /dev/null \
    || count_failure "vim plugin update failed."

echo_info "Google cloud command update"
if command -v gcloud > /dev/null 2>&1; then
    yes | gcloud components update || count_failure "gcloud components update failed."
fi

echo_info "GitHub Copilot update"
# 'gh extension upgrade' fails outright when the extension is not installed,
# so only upgrade what is actually there.
if command -v gh > /dev/null 2>&1 && gh extension list 2>/dev/null | grep -q "gh-copilot"; then
    gh extension upgrade gh-copilot || count_failure "gh extension upgrade gh-copilot failed."
fi

echo_info "google key"
# wget -O truncates the destination before it even connects, so download to a
# temporary file and replace the existing pem only after a successful download.
roots_pem_tmp="${TMPDIR:-/tmp}/google-roots.pem.$$"
if wget -q "https://pki.goog/roots.pem" -O "$roots_pem_tmp"; then
    mv "$roots_pem_tmp" ~/secrets/google-roots.pem
    echo_ok "google-roots.pem updated."
else
    rm -f "$roots_pem_tmp"
    count_failure "Failed to download roots.pem. The existing file is kept."
fi

routine_exit_status
