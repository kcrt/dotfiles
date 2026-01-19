#!/bin/bash
# Cross-platform git credential helper
# Automatically selects the appropriate credential helper based on OS

case "$(uname)" in
    Darwin)
        exec git credential-osxkeychain "$@"
        ;;
    Linux)
        exec git credential-cache --timeout=3600 "$@"
        ;;
    *)
        # Fallback to cache for unknown systems
        exec git credential-cache --timeout=3600 "$@"
        ;;
esac
