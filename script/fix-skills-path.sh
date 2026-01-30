#!/usr/bin/env bash
# -*- coding: utf-8 -*-

#===============================================================================
#
#          FILE:  fix-skills-path.sh
#
#         USAGE:  ./fix-skills-path.sh
#
#   DESCRIPTION:  Fix broken symlinks in ~/.claude/skills/ that were created
#                 with incorrect relative paths when using GNU Stow.
#                 Skills are installed to ~/.agents/skills/ and symlinked to
#                 ~/.claude/skills/, but the symlinks use relative paths that
#                 assume ~/.claude is a regular directory, not a symlink.
#
#       OPTIONS:  ---
#  REQUIREMENTS:  bash, GNU coreutils
#          BUGS:  ---
#         NOTES:  ---
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#      REVISION:  $Id$
#
#===============================================================================

set -euo pipefail

SKILLS_DIR="${HOME}/.claude/skills"
TARGET_BASE=".agents/skills"
FIXED_COUNT=0
SKIPPED_COUNT=0

# Check if skills directory exists
if [[ ! -d "${SKILLS_DIR}" ]]; then
    echo "Error: ${SKILLS_DIR} does not exist."
    exit 1
fi

echo "Scanning ${SKILLS_DIR} for broken symlinks..."

for item in "${SKILLS_DIR}"/*; do
    if [[ -L "${item}" ]]; then
        current_target=$(readlink "${item}")

        # Only process symlinks pointing to .agents/skills
        if [[ "${current_target}" == *"${TARGET_BASE}"* ]]; then
            if [[ ! -e "${item}" ]]; then
                # Broken symlink - check if correct target exists
                skill_name=$(basename "${current_target}")
                correct_target="${HOME}/${TARGET_BASE}/${skill_name}"

                if [[ -e "${correct_target}" ]]; then
                    # Target exists, fix the symlink
                    rm "${item}"
                    ln -s "../../../../${TARGET_BASE}/${skill_name}" "${item}"
                    echo "Fixed: ${skill_name}"
                    FIXED_COUNT=$((FIXED_COUNT + 1))
                else
                    # Target doesn't exist - skip (leave broken as-is)
                    echo "Skipped: ${skill_name} (not found in ${correct_target})"
                    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
                fi
            fi
        fi
    fi
done

echo ""
echo "Summary:"
echo "  Fixed:   ${FIXED_COUNT} symlinks"
echo "  Skipped: ${SKIPPED_COUNT} symlinks"
