#
#	656-functions_zai.zsh
#		Z.ai API proxy for Claude
#

function zai_on() {
	# Check if ZAI_API_KEY is set
	if [[ -z "$ZAI_API_KEY" ]]; then
		echo "Error: ZAI_API_KEY environment variable is not set. Please set it to use Z.ai model."
		return 1
	fi
	echo_info "Z.ai model enabled for Claude. (Use zai_off to disable)"
	touch ~/use-zai
	export ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
	export ANTHROPIC_AUTH_TOKEN=$ZAI_API_KEY
}

function zai_off() {
	echo "Z.ai model disabled for Claude."
	rm -f ~/use-zai
	unset ANTHROPIC_BASE_URL
	unset ANTHROPIC_AUTH_TOKEN
}

# if there is ~/use-zai file, use Z.ai model for Claude
if [[ -f ~/use-zai ]]; then
	zai_on
fi
