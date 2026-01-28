#
#	656-functions_zai.zsh
#		Z.ai API proxy for Claude
#

# Helper function to set environment variables for Claude Code targets
function _claude-code-set-env() {
	local target=$1
	local model=$2

	case "$target" in
		anthropic)
			unset ANTHROPIC_BASE_URL
			unset ANTHROPIC_AUTH_TOKEN
			unset ANTHROPIC_MODEL
			unset ANTHROPIC_DEFAULT_OPUS_MODEL
			unset ANTHROPIC_DEFAULT_SONNET_MODEL
			unset ANTHROPIC_DEFAULT_HAIKU_MODEL
			unset CLAUDE_CODE_SUBAGENT_MODEL
			;;
		zai)
			export ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
			export ANTHROPIC_AUTH_TOKEN=$ZAI_API_KEY
			export ANTHROPIC_MODEL=GLM-4.7
			export ANTHROPIC_DEFAULT_OPUS_MODEL=GLM-4.7
			export ANTHROPIC_DEFAULT_SONNET_MODEL=GLM-4.7
			export ANTHROPIC_DEFAULT_HAIKU_MODEL=GLM-4.5-Air
			export CLAUDE_CODE_SUBAGENT_MODEL=GLM-4.7
			;;
		kimi)
			export ANTHROPIC_BASE_URL=https://api.moonshot.ai/anthropic
			export ANTHROPIC_AUTH_TOKEN=${MOONSHOT_API_KEY}
			export ANTHROPIC_MODEL=kimi-k2.5
			export ANTHROPIC_DEFAULT_OPUS_MODEL=kimi-k2.5
			export ANTHROPIC_DEFAULT_SONNET_MODEL=kimi-k2.5
			export ANTHROPIC_DEFAULT_HAIKU_MODEL=kimi-k2.5
			export CLAUDE_CODE_SUBAGENT_MODEL=kimi-k2.5
			;;
		ollama)
			if [[ -n "$model" ]]; then
				export ANTHROPIC_BASE_URL=http://localhost:11434
				export ANTHROPIC_AUTH_TOKEN=ollama
				export ANTHROPIC_MODEL=$model
				export ANTHROPIC_DEFAULT_OPUS_MODEL=$model
				export ANTHROPIC_DEFAULT_SONNET_MODEL=$model
				export ANTHROPIC_DEFAULT_HAIKU_MODEL=$model
				export CLAUDE_CODE_SUBAGENT_MODEL=$model
			fi
			;;
	esac
}

function claude-code-to() {
	# Check if jq is available
	if ! command -v jq &>/dev/null; then
		echo "Error: jq is required but not installed."
		echo "Install it with: brew install jq"
		return 1
	fi

	local target=$1
	local config_file="$HOME/.claude-code-to.json"

	if [[ -z "$target" ]]; then
		# Show current configuration
		if [[ -f "$config_file" ]]; then
			local current=$(jq -r '.target // "anthropic"' "$config_file" 2>/dev/null)
			echo "Current Claude Code target: $current"
		else
			echo "Usage: claude-code-to [anthropic|zai|kimi|ollama:MODEL]"
			echo ""
			echo "Examples:"
			echo "  claude-code-to anthropic          # Use Anthropic API directly"
			echo "  claude-code-to zai                # Use Z.ai proxy"
			echo "  claude-code-to kimi               # Use Kimi (Moonshot AI)"
			echo "  claude-code-to ollama:qwen3-coder # Use Ollama with qwen3-coder"
			echo "  claude-code-to ollama:gpt-oss:20b # Use Ollama with gpt-oss:20b"
		fi
		return 0
	fi

	case "$target" in
		anthropic)
			echo "Anthropic API (direct) enabled for Claude."
			echo '{"target":"anthropic"}' > "$config_file"
			_claude-code-set-env "anthropic"
			;;
		zai)
			# Check if ZAI_API_KEY is set
			if [[ -z "$ZAI_API_KEY" ]]; then
				echo "Error: ZAI_API_KEY environment variable is not set. Please set it to use Z.ai model."
				return 1
			fi
			echo_info "Z.ai proxy enabled for Claude."
			echo '{"target":"zai"}' > "$config_file"
			_claude-code-set-env "zai"
			;;
		kimi)
			if [[ -z "$MOONSHOT_API_KEY" ]]; then
				echo "Error: MOONSHOT_API_KEY environment variable is not set. Please set it to use Kimi."
				return 1
			fi
			echo_info "Kimi (Moonshot AI) enabled for Claude."
			echo '{"target":"kimi"}' > "$config_file"
			_claude-code-set-env "kimi"
			;;
		ollama:*)
			local model="${target#ollama:}"
			echo_info "Ollama ($model) enabled for Claude."
			echo "{\"target\":\"ollama\",\"model\":\"$model\"}" > "$config_file"
			_claude-code-set-env "ollama" "$model"
			;;
		*)
			echo "Error: Unknown target '$target'."
			echo ""
			echo "Valid options:"
			echo "  anthropic              - Use Anthropic API directly"
			echo "  zai                    - Use Z.ai proxy"
			echo "  kimi                   - Use Kimi (Moonshot AI)"
			echo "  ollama:MODEL_NAME      - Use Ollama with specified model"
			return 1
			;;
	esac
}

# Restore configuration from config file on shell load
local config_file="$HOME/.claude-code-to.json"
if [[ -f "$config_file" ]]; then
	local target=$(jq -r '.target // "anthropic"' "$config_file" 2>/dev/null)
	local model=$(jq -r '.model // ""' "$config_file" 2>/dev/null)
	case "$target" in
		zai)
			if [[ -n "$ZAI_API_KEY" ]]; then
				_claude-code-set-env "zai"
				echo_info "Z.ai proxy enabled for Claude."
			fi
			;;
	kimi)
			if [[ -n "$MOONSHOT_API_KEY" ]]; then
				_claude-code-set-env "kimi"
				echo_info "Kimi (Moonshot AI) enabled for Claude."
			fi
			;;
		ollama)
			if [[ -n "$model" ]]; then
				_claude-code-set-env "ollama" "$model"
				echo_info "Ollama ($model) enabled for Claude."
			fi
			;;
	esac
fi
