#
#	656-functions_claudecode.zsh
#		Launch Claude Code against another provider (Z.ai, DeepSeek, ...)
#

# Default model used when a Z.ai target is given without an explicit model.
_CLAUDE_CODE_ZAI_DEFAULT_MODEL=glm-5.3
_CLAUDE_CODE_ZAI_HAIKU_MODEL=glm-5.3-flash

# Helper function to show help text
function _claude-code-show-help() {
	cat <<'EOF'
Usage:
  claude-code-to TARGET [ARGS]   # Launch `claude ARGS` against TARGET
                                 #   (the current shell environment is not modified)

Targets: anthropic | zai[:MODEL] | kimi | deepseek:MODEL | ollama:MODEL | lmstudio:MODEL | openrouter:MODEL

API keys come from with-secret, which asks for Touch ID on every launch.

Examples:
  claude-code-to zai                              # Z.ai (default model)
  claude-code-to zai:MODEL                        # Z.ai with specified model
  claude-code-to kimi                             # Kimi (Moonshot AI)
  claude-code-to "deepseek:deepseek-flash[1m]"    # DeepSeek with specified model
  claude-code-to ollama:MODEL                     # Ollama with specified model
  claude-code-to lmstudio:MODEL                   # LM Studio with specified model
  claude-code-to openrouter:MODEL                 # OpenRouter with specified model
  claude-code-to deepseek:MODEL -c                # Forward extra args to `claude`
EOF
}

# List available models for a model-requiring provider.
function _claude-code-list-models() {
	local provider=$1
	local prefix=claude-code-to

	case "$provider" in
		zai)
			echo "Available models:"
			echo "  $prefix zai:glm-5.3         # GLM-5.3"
			echo "  $prefix zai:glm-5.3-flash   # GLM-5.3 Flash"
			;;
		deepseek)
			echo "Available models:"
			echo "  $prefix deepseek:deepseek-v4-pro     # DeepSeek V4 Pro"
			echo "  $prefix deepseek:deepseek-flash      # DeepSeek V4.1 Flash"
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

# Check that the target is known and has a model when it needs one.
# Echoes errors and returns non-zero on failure.
function _claude-code-validate() {
	local provider=$1
	local model=$2

	case "$provider" in
		anthropic|zai|kimi)
			;;
		deepseek|openrouter|ollama|lmstudio)
			if [[ -z "$model" ]]; then
				echo "Error: $provider requires a model."
				echo ""
				_claude-code-list-models "$provider"
				return 1
			fi
			;;
		*)
			echo "Error: Unknown target '$provider'."
			echo ""
			_claude-code-show-help
			return 1
			;;
	esac
	return 0
}

# The with-secret name holding the API key for a provider (none for local ones).
function _claude-code-secret-name() {
	case "$1" in
		zai) echo ZAI_API_KEY ;;
		kimi) echo MOONSHOT_API_KEY ;;
		deepseek) echo DEEPSEEK_API_KEY ;;
		openrouter) echo OPENROUTER_API_KEY ;;
	esac
}

# Export the provider's endpoint and model settings. Meant to run in a
# subshell. The API key itself is added later by with-secret.
function _claude-code-export-env() {
	local provider=$1
	local model=$2

	# Claude Code prefers ANTHROPIC_API_KEY over ANTHROPIC_AUTH_TOKEN.
	unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN

	local base_url haiku_model=""
	case "$provider" in
		zai)
			base_url=https://api.z.ai/api/anthropic
			model=${model:-$_CLAUDE_CODE_ZAI_DEFAULT_MODEL}
			haiku_model=$_CLAUDE_CODE_ZAI_HAIKU_MODEL
			;;
		kimi)
			base_url=https://api.moonshot.ai/anthropic
			model=kimi-k2.5
			;;
		deepseek)
			base_url=https://api.deepseek.com/anthropic
			haiku_model=deepseek-flash
			;;
		openrouter)
			base_url=https://openrouter.ai/api
			;;
		ollama)
			base_url=http://localhost:11434
			export ANTHROPIC_AUTH_TOKEN=ollama
			;;
		lmstudio)
			base_url=http://localhost:1234
			export ANTHROPIC_AUTH_TOKEN=lm-studio
			;;
	esac

	export ANTHROPIC_BASE_URL=$base_url
	export ANTHROPIC_MODEL=$model
	export ANTHROPIC_DEFAULT_OPUS_MODEL=$model
	export ANTHROPIC_DEFAULT_SONNET_MODEL=$model
	export ANTHROPIC_DEFAULT_HAIKU_MODEL=${haiku_model:-$model}
	export CLAUDE_CODE_SUBAGENT_MODEL=$model
}

function claude-code-to() {
	local target=$1
	if [[ -z "$target" || "$target" == "--help" || "$target" == "-h" ]]; then
		_claude-code-show-help
		return 0
	fi
	shift

	local provider="${target%%:*}"
	local model=""
	[[ "$target" == *:* ]] && model="${target#*:}"
	_claude-code-validate "$provider" "$model" || return 1

	if [[ "$provider" == "anthropic" ]]; then
		command claude "$@"
		return $?
	fi

	local secret_name=$(_claude-code-secret-name "$provider")
	(
		_claude-code-export-env "$provider" "$model"
		if [[ -z "$secret_name" ]]; then
			command claude "$@"
		else
			# with-secret puts the key in the environment under its own name;
			# zsh renames it to the variable Claude Code reads and drops the original.
			with-secret "$secret_name" -- /bin/zsh -fc \
				'export ANTHROPIC_AUTH_TOKEN=${(P)1}; unset $1; shift; exec claude "$@"' \
				claude-code-to "$secret_name" "$@"
		fi
	)
}
