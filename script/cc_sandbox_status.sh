#!/bin/sh
# Show Claude Code bash sandbox status for ccstatusline.
# Resolves the `sandbox.enabled` setting with the same layering Claude Code
# uses: project settings win over user settings, .local over the plain file.
# 🏖️ = sandboxed, 🏕 = not sandboxed.

for f in \
	"$PWD/.claude/settings.local.json" \
	"$PWD/.claude/settings.json" \
	"$HOME/.claude/settings.local.json" \
	"$HOME/.claude/settings.json"
do
	[ -f "$f" ] || continue
	enabled=$(jq -r '.sandbox.enabled // empty' "$f" 2>/dev/null)
	case "$enabled" in
		true) echo "🏖️"; exit 0;;
		false) echo "🏕"; exit 0;;
	esac
done

echo "🏕"
