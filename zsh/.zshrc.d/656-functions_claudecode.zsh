#
#	656-functions_claudecode.zsh
#		Z.ai API proxy for Claude
#

# Helper function to show help text
function _claude-code-show-help() {
	cat <<'EOF'
Usage:
  claude-code-to [TARGET]              # Switch the current shell to TARGET
  claude-code-to --run TARGET [ARGS]   # Launch `claude ARGS` with TARGET in a subshell
                                       #   (current shell environment is not modified)

Targets: anthropic | zai | kimi | deepseek:MODEL | ollama:MODEL | lmstudio:MODEL | openrouter:MODEL

Examples:
  claude-code-to anthropic                 # Use Anthropic API directly
  claude-code-to zai                       # Use Z.ai proxy
  claude-code-to kimi                      # Use Kimi (Moonshot AI)
  claude-code-to deepseek:MODEL            # Use DeepSeek with specified model
  claude-code-to ollama:MODEL              # Use Ollama with specified model
  claude-code-to lmstudio:MODEL            # Use LM Studio with specified model
  claude-code-to openrouter:MODEL          # Use OpenRouter with specified model
  claude-code-to --run zai                 # One-shot: run `claude` against Z.ai
  claude-code-to --run deepseek:MODEL -c   # Forward extra args to `claude`
EOF
}

# List available models for a model-requiring provider.
# $2 is the command prefix used in the suggestions (e.g. "claude-code-to" or
# "claude-code-to --run"), defaulting to "claude-code-to".
function _claude-code-list-models() {
	local provider=$1
	local prefix=${2:-claude-code-to}

	case "$provider" in
		deepseek)
			echo "Available models:"
			echo "  $prefix deepseek:deepseek-v4-pro     # DeepSeek V4 Pro"
			echo "  $prefix deepseek:deepseek-v4-flash   # DeepSeek V4 Flash"
			;;
		openrouter)
			echo "Available models:"
			echo "  $prefix openrouter:minimax/minimax-m2.5        # MiniMax M2.5"
			echo "  $prefix openrouter:moonshotai/kimi-k2.5        # Kimi K2.5"
			echo "  $prefix openrouter:openai/gpt-oss-120b:nitro   # GPT-OSS 120B (nitro)"
			echo "  $prefix openrouter:z-ai/glm-5                  # GLM-5"
			;;
		ollama)
			echo "Available Ollama models:"
			if ! ollama list 2>/dev/null | tail -n +2 | awk -v p="$prefix" '{print "  " p " ollama:" $1}'; then
				echo "  (could not run ollama — is it installed and running?)"
			fi
			;;
		lmstudio)
			echo "Available LM Studio models:"
			local models
			models=$(curl -sf http://localhost:1234/v1/models 2>/dev/null | jq -r '.data[].id' 2>/dev/null)
			if [[ -z "$models" ]]; then
				echo "  (could not reach LM Studio at http://localhost:1234 — is it running?)"
			else
				echo "$models" | while read -r m; do
					echo "  $prefix lmstudio:$m"
				done
			fi
			;;
	esac
}

# Validate target+model and required env vars for a one-shot run.
# Echoes errors and returns non-zero on failure.
function _claude-code-validate() {
	local provider=$1
	local model=$2

	case "$provider" in
		anthropic)
			;;
		zai)
			[[ -z "$ZAI_API_KEY" ]] && { echo "Error: ZAI_API_KEY environment variable is not set."; return 1; }
			;;
		kimi)
			[[ -z "$MOONSHOT_API_KEY" ]] && { echo "Error: MOONSHOT_API_KEY environment variable is not set."; return 1; }
			;;
		deepseek)
			[[ -z "$model" ]] && { echo "Error: deepseek requires a model."; echo ""; _claude-code-list-models deepseek "claude-code-to --run"; return 1; }
			[[ -z "$DEEPSEEK_API_KEY" ]] && { echo "Error: DEEPSEEK_API_KEY environment variable is not set."; return 1; }
			;;
		openrouter)
			[[ -z "$model" ]] && { echo "Error: openrouter requires a model."; echo ""; _claude-code-list-models openrouter "claude-code-to --run"; return 1; }
			[[ -z "$OPENROUTER_API_KEY" ]] && { echo "Error: OPENROUTER_API_KEY environment variable is not set."; return 1; }
			;;
		ollama)
			[[ -z "$model" ]] && { echo "Error: ollama requires a model."; echo ""; _claude-code-list-models ollama "claude-code-to --run"; return 1; }
			;;
		lmstudio)
			[[ -z "$model" ]] && { echo "Error: lmstudio requires a model."; echo ""; _claude-code-list-models lmstudio "claude-code-to --run"; return 1; }
			;;
		*)
			echo "Error: Unknown target '$provider'."
			return 1
			;;
	esac
	return 0
}

# Providers other than Anthropic authenticate via ANTHROPIC_AUTH_TOKEN, and
# Claude Code prefers ANTHROPIC_API_KEY when both are present. Mask it with an
# empty value while a proxy target is active, stashing the original so that
# switching back to `anthropic` restores it.
function _claude-code-mask-api-key() {
	[[ -z ${_CLAUDE_CODE_TO_SAVED_API_KEY+x} ]] && export _CLAUDE_CODE_TO_SAVED_API_KEY="${ANTHROPIC_API_KEY-}"
	export ANTHROPIC_API_KEY=""
}

function _claude-code-restore-api-key() {
	if [[ -n "${_CLAUDE_CODE_TO_SAVED_API_KEY-}" ]]; then
		export ANTHROPIC_API_KEY="$_CLAUDE_CODE_TO_SAVED_API_KEY"
	else
		unset ANTHROPIC_API_KEY
	fi
	unset _CLAUDE_CODE_TO_SAVED_API_KEY
}

# Helper function to set environment variables for Claude Code targets
function _claude-code-set-env() {
	local target=$1
	local model=$2

	# Model-requiring providers cannot be configured without a model
	case "$target" in
		deepseek|openrouter|ollama|lmstudio)
			[[ -z "$model" ]] && return 0
			;;
	esac

	if [[ "$target" == "anthropic" ]]; then
		_claude-code-restore-api-key
	else
		_claude-code-mask-api-key
	fi

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
			export ANTHROPIC_MODEL=GLM-5.3
			export ANTHROPIC_DEFAULT_OPUS_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_SONNET_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_HAIKU_MODEL=GLM-5.3-Flash
			export CLAUDE_CODE_SUBAGENT_MODEL=$ANTHROPIC_MODEL
			;;
		kimi)
			export ANTHROPIC_BASE_URL=https://api.moonshot.ai/anthropic
			export ANTHROPIC_AUTH_TOKEN=$MOONSHOT_API_KEY
			export ANTHROPIC_MODEL=kimi-k2.5
			export ANTHROPIC_DEFAULT_OPUS_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_SONNET_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_HAIKU_MODEL=$ANTHROPIC_MODEL
			export CLAUDE_CODE_SUBAGENT_MODEL=$ANTHROPIC_MODEL
			;;
		deepseek)
			export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
			export ANTHROPIC_AUTH_TOKEN=$DEEPSEEK_API_KEY
			export ANTHROPIC_MODEL=$model
			export ANTHROPIC_DEFAULT_OPUS_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_SONNET_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-flash
			export CLAUDE_CODE_SUBAGENT_MODEL=$ANTHROPIC_MODEL
			;;
		openrouter)
			export ANTHROPIC_BASE_URL=https://openrouter.ai/api
			export ANTHROPIC_AUTH_TOKEN=$OPENROUTER_API_KEY
			export ANTHROPIC_MODEL=$model
			export ANTHROPIC_DEFAULT_OPUS_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_SONNET_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_HAIKU_MODEL=$ANTHROPIC_MODEL
			export CLAUDE_CODE_SUBAGENT_MODEL=$ANTHROPIC_MODEL
			;;
		ollama)
			export ANTHROPIC_BASE_URL=http://localhost:11434
			export ANTHROPIC_AUTH_TOKEN=ollama
			export ANTHROPIC_MODEL=$model
			export ANTHROPIC_DEFAULT_OPUS_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_SONNET_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_HAIKU_MODEL=$ANTHROPIC_MODEL
			export CLAUDE_CODE_SUBAGENT_MODEL=$ANTHROPIC_MODEL
			;;
		lmstudio)
			export ANTHROPIC_BASE_URL=http://localhost:1234
			export ANTHROPIC_AUTH_TOKEN=lm-studio
			export ANTHROPIC_MODEL=$model
			export ANTHROPIC_DEFAULT_OPUS_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_SONNET_MODEL=$ANTHROPIC_MODEL
			export ANTHROPIC_DEFAULT_HAIKU_MODEL=$ANTHROPIC_MODEL
			export CLAUDE_CODE_SUBAGENT_MODEL=$ANTHROPIC_MODEL
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

	# --run: launch `claude` in a subshell with the target's env vars set,
	# without modifying the current shell or the persisted config file.
	if [[ "$1" == "--run" ]]; then
		shift
		local run_target=$1
		if [[ -z "$run_target" ]]; then
			echo "Error: --run requires a target."
			echo ""
			_claude-code-show-help
			return 1
		fi
		shift
		local run_provider="${run_target%%:*}"
		local run_model=""
		[[ "$run_target" == *:* ]] && run_model="${run_target#*:}"
		if ! _claude-code-validate "$run_provider" "$run_model"; then
			return 1
		fi
		(
			_claude-code-set-env "$run_provider" "$run_model"
			command claude "$@"
		)
		return $?
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
		deepseek)
			echo "Error: DeepSeek requires a model to be specified."
			echo ""
			_claude-code-list-models deepseek
			return 1
			;;
		deepseek:*)
			local model="${target#deepseek:}"
			if [[ -z "$DEEPSEEK_API_KEY" ]]; then
				echo "Error: DEEPSEEK_API_KEY environment variable is not set. Please set it to use DeepSeek."
				return 1
			fi
			echo_info "DeepSeek ($model) enabled for Claude."
			echo "{\"target\":\"deepseek\",\"model\":\"$model\"}" > "$config_file"
			_claude-code-set-env "deepseek" "$model"
			;;
		ollama)
			_claude-code-list-models ollama
			return 1
			;;
		ollama:*)
			local model="${target#ollama:}"
			echo_info "Ollama ($model) enabled for Claude."
			echo "{\"target\":\"ollama\",\"model\":\"$model\"}" > "$config_file"
			_claude-code-set-env "ollama" "$model"
			;;
		lmstudio)
			_claude-code-list-models lmstudio
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
			_claude-code-list-models openrouter
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
			echo "  deepseek:MODEL_NAME    - Use DeepSeek with specified model"
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
		deepseek)
			if [[ -n "$model" ]] && [[ -n "$DEEPSEEK_API_KEY" ]]; then
				_claude-code-set-env "deepseek" "$model"
				echo_info "DeepSeek ($model) enabled for Claude."
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
