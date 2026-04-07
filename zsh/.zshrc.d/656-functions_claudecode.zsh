#
#	656-functions_claudecode.zsh
#		Z.ai API proxy for Claude
#

# Helper function to show help text
function _claude-code-show-help() {
	cat <<'EOF'
Usage: claude-code-to [anthropic|zai|kimi|ollama:MODEL|lmstudio:MODEL|openrouter:MODEL]

Examples:
  claude-code-to anthropic          # Use Anthropic API directly
  claude-code-to zai                # Use Z.ai proxy
  claude-code-to kimi               # Use Kimi (Moonshot AI)
  claude-code-to ollama:MODEL       # Use Ollama with specified model
  claude-code-to lmstudio:MODEL     # Use LM Studio with specified model
  claude-code-to openrouter:MODEL   # Use OpenRouter with specified model
EOF
}

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
			export ANTHROPIC_MODEL=GLM-5.1
			export ANTHROPIC_DEFAULT_OPUS_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_SONNET_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_HAIKU_MODEL=GLM-4.5-Air
			export CLAUDE_CODE_SUBAGENT_MODEL=GLM-5.1
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
		openrouter)
			if [[ -n "$model" ]]; then
				export ANTHROPIC_BASE_URL=https://openrouter.ai/api
				export ANTHROPIC_AUTH_TOKEN=$OPENROUTER_API_KEY
				export ANTHROPIC_API_KEY=""  # Important: Must be explicitly empty
				export ANTHROPIC_MODEL=$model
				export ANTHROPIC_DEFAULT_OPUS_MODEL=$model
				export ANTHROPIC_DEFAULT_SONNET_MODEL=$model
				export ANTHROPIC_DEFAULT_HAIKU_MODEL=$model
				export CLAUDE_CODE_SUBAGENT_MODEL=$model
			fi
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
		lmstudio)
			if [[ -n "$model" ]]; then
				export ANTHROPIC_BASE_URL=http://localhost:1234
				export ANTHROPIC_AUTH_TOKEN=lm-studio
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
			_claude-code-show-help
		fi
		return 0
	fi

	case "$target" in
		--help|-h)
			_claude-code-show-help
			return 0
			;;
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
		ollama)
			echo "Available Ollama models:"
			if ! ollama list 2>/dev/null | tail -n +2 | awk '{print "  claude-code-to ollama:" $1}'; then
				echo "  (could not run ollama — is it installed and running?)"
			fi
			return 1
			;;
		ollama:*)
			local model="${target#ollama:}"
			echo_info "Ollama ($model) enabled for Claude."
			echo "{\"target\":\"ollama\",\"model\":\"$model\"}" > "$config_file"
			_claude-code-set-env "ollama" "$model"
			;;
		lmstudio)
			echo "Available LM Studio models:"
			local models
			models=$(curl -sf http://localhost:1234/v1/models 2>/dev/null | jq -r '.data[].id' 2>/dev/null)
			if [[ -z "$models" ]]; then
				echo "  (could not reach LM Studio at http://localhost:1234 — is it running?)"
			else
				echo "$models" | while read -r m; do
					echo "  claude-code-to lmstudio:$m"
				done
			fi
			return 1
			;;
		lmstudio:*)
			local model="${target#lmstudio:}"
			echo_info "LM Studio ($model) enabled for Claude."
			echo "{\"target\":\"lmstudio\",\"model\":\"$model\"}" > "$config_file"
			_claude-code-set-env "lmstudio" "$model"
			;;
		openrouter)
			echo "Error: OpenRouter requires a model to be specified."
			echo ""
			echo "Available models:"
			echo "  claude-code-to openrouter:minimax/minimax-m2.5           # MiniMax M2.5"
			echo "  claude-code-to openrouter:moonshotai/kimi-k2.5          # Kimi K2.5"
			echo "  claude-code-to openrouter:openai/gpt-oss-120b:nitro     # GPT-OSS 120B (nitro)"
			echo "  claude-code-to openrouter:z-ai/glm-5                    # GLM-5"
			return 1
			;;
		openrouter:*)
			local model="${target#openrouter:}"
			if [[ -z "$OPENROUTER_API_KEY" ]]; then
				echo "Error: OPENROUTER_API_KEY environment variable is not set. Please set it to use OpenRouter."
				return 1
			fi
			echo_info "OpenRouter ($model) enabled for Claude."
			echo "{\"target\":\"openrouter\",\"model\":\"$model\"}" > "$config_file"
			_claude-code-set-env "openrouter" "$model"
			;;
		*)
			echo "Error: Unknown target '$target'."
			echo ""
			echo "Valid options:"
			echo "  anthropic              - Use Anthropic API directly"
			echo "  zai                    - Use Z.ai proxy"
			echo "  kimi                   - Use Kimi (Moonshot AI)"
			echo "  ollama:MODEL_NAME      - Use Ollama with specified model"
			echo "  lmstudio:MODEL_NAME    - Use LM Studio with specified model"
			echo "  openrouter:MODEL_NAME  - Use OpenRouter with specified model"
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
		lmstudio)
			if [[ -n "$model" ]]; then
				_claude-code-set-env "lmstudio" "$model"
				echo_info "LM Studio ($model) enabled for Claude."
			fi
			;;
		openrouter)
			if [[ -n "$model" ]] && [[ -n "$OPENROUTER_API_KEY" ]]; then
				_claude-code-set-env "openrouter" "$model"
				echo_info "OpenRouter ($model) enabled for Claude."
			fi
			;;
	esac
fi
