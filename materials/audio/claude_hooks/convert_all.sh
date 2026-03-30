#!/bin/bash
# Convert all ABC notation files to M4A in this directory
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAYABC="$HOME/dotfiles/script/playabc.sh"

[[ -f "$PLAYABC" ]] || { echo "Error: $PLAYABC not found" >&2; exit 1; }

for abc in "$SCRIPT_DIR"/*.abc; do
    name=$(basename "$abc" .abc)
    output="$SCRIPT_DIR/${name}.m4a"
    echo "Converting: $name"
    bash "$PLAYABC" -o "$output" "$abc"
    echo "  -> $output"
done

echo "Done."
