# detect-project-version.sh — Shared version detection for project files
# Usage: source this file, then call detect_project_versions or check_version_consistency
# Do NOT add set -e / set -u here; consumers control their own shell options.

# Internal: read file content from working tree or a specific git ref
# Usage: _read_file_content <filepath> [git-ref]
_read_file_content() {
  local filepath="$1"
  local ref="${2:-}"
  if [[ -n "$ref" ]]; then
    git show "$ref":"$filepath" 2>/dev/null
  else
    cat "$filepath" 2>/dev/null
  fi
}

# Internal: find .pbxproj file path
# Usage: _find_pbxproj [git-ref]
_find_pbxproj() {
  local ref="${1:-}"
  if [[ -n "$ref" ]]; then
    git ls-tree -r --name-only "$ref" 2>/dev/null | grep '\.pbxproj$' | head -1
  else
    find . -name '*.pbxproj' -print -quit 2>/dev/null | sed 's|^\./||'
  fi
}

# Detect versions from project files
# Usage: detect_project_versions [git-ref]
# Output: tab-separated lines "source\tversion" for each detected version
# Returns: 0 if at least one version found, 1 if none
detect_project_versions() {
  local ref="${1:-}"
  local found=0

  # package.json
  local pkg_version
  pkg_version=$(_read_file_content "package.json" "$ref" | sed -n 's/.*"version".*:.*"\([^"]*\)".*/\1/p')
  if [[ -n "$pkg_version" ]]; then
    printf 'package.json\t%s\n' "$pkg_version"
    found=1
  fi

  # Cargo.toml (Rust)
  local cargo_version
  cargo_version=$(_read_file_content "Cargo.toml" "$ref" | sed -n 's/^version *= *"\([^"]*\)".*/\1/p')
  if [[ -n "$cargo_version" ]]; then
    printf 'Cargo.toml\t%s\n' "$cargo_version"
    found=1
  fi

  # pyproject.toml (Python)
  local py_version
  py_version=$(_read_file_content "pyproject.toml" "$ref" | sed -n 's/^version *= *"\([^"]*\)".*/\1/p')
  if [[ -n "$py_version" ]]; then
    printf 'pyproject.toml\t%s\n' "$py_version"
    found=1
  fi

  # pubspec.yaml (Flutter/Dart) — version: 1.2.3+N, compare only semver part
  local pub_version
  pub_version=$(_read_file_content "pubspec.yaml" "$ref" | sed -n 's/^version: *\([0-9][0-9.]*\).*/\1/p')
  if [[ -n "$pub_version" ]]; then
    printf 'pubspec.yaml\t%s\n' "$pub_version"
    found=1
  fi

  # Xcode project (MARKETING_VERSION in .pbxproj)
  # Extract only from non-test targets: parse build setting blocks and skip
  # those whose PRODUCT_BUNDLE_IDENTIFIER contains "Test"
  local pbxproj
  pbxproj=$(_find_pbxproj "$ref")
  if [[ -n "$pbxproj" ]]; then
    local xcode_versions
    xcode_versions=$(_read_file_content "$pbxproj" "$ref" | awk '
      /buildSettings/ { p=1; mv=""; is_test=0; next }
      p && /MARKETING_VERSION/ { gsub(/.*= */, ""); gsub(/;.*/, ""); mv=$0 }
      p && /PRODUCT_BUNDLE_IDENTIFIER/ && /[Tt]est/ { is_test=1 }
      p && /\};/ { if (mv != "" && is_test == 0) print mv; p=0 }
    ' | sort -u)
    while IFS= read -r xv; do
      if [[ -n "$xv" ]]; then
        printf 'Xcode (MARKETING_VERSION)\t%s\n' "$xv"
        found=1
      fi
    done <<< "$xcode_versions"
  fi

  return $(( found == 0 ))
}

# Check version consistency against an expected version
# Usage: check_version_consistency <expected-version> [git-ref]
# Output: lines for mismatches only (e.g. "  package.json: 1.2.3")
# Returns: 0 if all match, 1 if any mismatch
check_version_consistency() {
  local expected="$1"
  local ref="${2:-}"
  local mismatch=0

  local versions
  versions=$(detect_project_versions "$ref") || return 0  # no versions found = no mismatch

  while IFS=$'\t' read -r source version; do
    if [[ -n "$version" && "$version" != "$expected" ]]; then
      echo "  $source: $version"
      mismatch=1
    fi
  done <<< "$versions"

  return "$mismatch"
}
