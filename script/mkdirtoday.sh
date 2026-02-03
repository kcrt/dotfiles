#!/usr/bin/env bash
set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: makedir_today.sh <name>" >&2
    echo "Example: makedir_today.sh analysis -> creates 20260202_analysis" >&2
    exit 1
fi

name="$1"
today=$(date +"%Y%m%d")
dir_name="${today}_${name}"

mkdir -p "$dir_name"
echo "Created: $dir_name"
