#!/bin/bash
set -euo pipefail

# git-autotag — Automatically create a version tag from project files
# Usage: git autotag [--dry-run] [--yes]

source "$(dirname "$0")/lib/detect-project-version.sh"

cd "$(git rev-parse --show-toplevel)"

dry_run=0
auto_yes=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) dry_run=1 ;;
    --yes|-y)  auto_yes=1 ;;
  esac
done

# Detect versions from project files
versions=$(detect_project_versions) || {
  echo "Error: No version found in project files (package.json, Cargo.toml, pyproject.toml, pubspec.yaml, *.pbxproj)" >&2
  exit 1
}

# Check for conflicting versions
unique_versions=$(echo "$versions" | cut -f2 | sort -u)
version_count=$(echo "$unique_versions" | wc -l | tr -d ' ')

if [[ "$version_count" -gt 1 ]]; then
  echo "Error: Conflicting versions detected:" >&2
  while IFS=$'\t' read -r source ver; do
    echo "  $source: $ver" >&2
  done <<< "$versions"
  exit 1
fi

version=$(echo "$unique_versions" | head -1)
tag="v${version}"

# Show detected sources
echo "Detected version $version from:"
while IFS=$'\t' read -r source ver; do
  echo "  $source"
done <<< "$versions"

# Check if tag already exists
if git rev-parse "$tag" >/dev/null 2>&1; then
  echo "Tag $tag already exists."
  exit 0
fi

# Check for dirty working tree
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
  echo "Error: Working tree is dirty. Commit or stash changes before tagging." >&2
  exit 1
fi

if [[ "$dry_run" -eq 1 ]]; then
  echo "Would create tag: $tag"
  exit 0
fi

if [[ "$auto_yes" -eq 0 ]]; then
  read -p "Create tag $tag? (Y/n) " answer </dev/tty
  if [[ "$answer" == [nN] ]]; then
    echo "Aborted."
    exit 1
  fi
fi

git tag "$tag"
echo "Created tag $tag"
