#!/bin/bash
# Remove worktrees created by `claude -w` and their branches.
# Scope: paths under .claude/worktrees/ and matching `worktree-*` branches.
# Refuses if a worktree has uncommitted changes (no --force).

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"

removed_any=0
while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    echo "Removing worktree: $path"
    git worktree remove "$path"
    removed_any=1
done < <(
    git worktree list --porcelain |
    awk '/^worktree /{p=substr($0,10); next} /^branch refs\/heads\/worktree-/{print p}' |
    grep -F "$repo_root/.claude/worktrees/" || true
)

while IFS= read -r branch; do
    [[ -z "$branch" ]] && continue
    echo "Deleting branch: $branch"
    git branch -D "$branch"
    removed_any=1
done < <(git branch --list 'worktree-*' | sed 's/^[* ]*//' || true)

if [[ "$removed_any" -eq 0 ]]; then
    echo "No Claude worktrees or worktree-* branches to clean."
fi
