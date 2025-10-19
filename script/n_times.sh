#!/bin/bash

# n_times.sh - Run a command n times
# Usage: ./n_times.sh <count> <command> [args...]

if [ $# -lt 2 ]; then
    echo "Usage: $0 <count> <command> [args...]" >&2
    echo "Example: $0 10 echo \"hello\"" >&2
    exit 1
fi

count=$1
shift

if ! [[ "$count" =~ ^[0-9]+$ ]]; then
    echo "Error: count must be a positive integer" >&2
    exit 1
fi

for ((i=1; i<=count; i++)); do
    echo "Iteration $i / $count ----"
    "$@"
done