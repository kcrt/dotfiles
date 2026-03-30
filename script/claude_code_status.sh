#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# Show Claude Code API target status icon for Zellij

# Determine target by checking config file first, then environment variable
local_config_file="$HOME/.claude-code-to.json"
target="anthropic"  # default

if [[ -f "$local_config_file" ]] && command -v jq &>/dev/null; then
    target=$(jq -r '.target // "anthropic"' "$local_config_file" 2>/dev/null)
elif [[ -n "${ANTHROPIC_BASE_URL}" ]]; then
    # Fallback to environment variable for backward compatibility
    if [[ "${ANTHROPIC_BASE_URL}" == *"z.ai"* ]]; then
        target="zai"
    elif [[ "${ANTHROPIC_BASE_URL}" == *"moonshot"* ]]; then
        target="kimi"
    elif [[ "${ANTHROPIC_BASE_URL}" == *"localhost:11434"* ]]; then
        target="ollama"
    elif [[ "${ANTHROPIC_BASE_URL}" == *"localhost:1234"* ]]; then
        target="lmstudio"
    elif [[ "${ANTHROPIC_BASE_URL}" == *"openrouter"* ]]; then
        target="openrouter"
    fi
fi

case "$target" in
    zai)
        echo "🅉"
        ;;
    kimi)
        echo "🥝"
        ;;
    ollama)
        echo "🦙"
        ;;
    lmstudio)
        echo "☰"
        ;;
    openrouter)
        echo "🔀"
        ;;
    *)
        # Default: anthropic
        echo "#[fg=#D08770]✺"
        ;;
esac
