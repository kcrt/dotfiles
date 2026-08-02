#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  generic_cargo_clean.sh
#         USAGE:  ./generic_cargo_clean.sh
#   DESCRIPTION:  Run 'cargo clean' on every Rust project under ~/prog so that
#                 build artifacts are not sent to the backup server.
#  REQUIREMENTS:  cargo
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

if ! command -v cargo > /dev/null 2>&1; then
    OSError "cargo is not installed. Please install it first."
    exit 1
fi

PROG_DIR=${PROG_DIR:-~/prog}
if [[ ! -d "$PROG_DIR" ]]; then
    OSError "$PROG_DIR not found."
    exit 1
fi

OSNotify "Cleaning up Rust projects..."
cd "$PROG_DIR" || exit 1
# Prune build artifacts and vendored crates; they contain their own Cargo.toml
# but are not projects of ours. venv holds the Rust sources that the Python
# cryptography package ships, which are workspace members without a root and
# so fail to clean. (The same directories are excluded from the QNAP backup.)
find . \( -name target -o -name node_modules -o -name .git -o -name venv -o -name .venv \) -prune \
    -o -name Cargo.toml -execdir cargo clean \;
# find returns 0 even when cargo clean fails, which is deliberate: a project
# that cannot be cleaned (a half-migrated workspace, say) is not worth failing
# the whole maintenance run over.
