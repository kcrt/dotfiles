#!/bin/bash
# Play all sounds in this directory (for development/testing)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAYSOUND="$HOME/dotfiles/script/playsound.sh"

[[ -f "$PLAYSOUND" ]] || { echo "Error: $PLAYSOUND not found" >&2; exit 1; }

for m4a in "$SCRIPT_DIR"/*.m4a; do
    name=$(basename "$m4a" .m4a)
    echo "▶ $name"
    bash "$PLAYSOUND" "$m4a"
done
