#
#	655-functions_llm.zsh
#		LLM (LM Studio) functions and configuration
#

LLM_MY_DEFAULT_MODEL='google/gemma-3-27b'
LLM_MY_HEAVY_MODEL='qwen/qwen3.5-35b-a3b'
LLM_MY_FAST_MODEL='google/gemma-3-4b'
LLM_MY_VISION_MODEL='qwen/qwen3.5-35b-a3b'
LLM_MY_OCR_MODEL='deepseek-ocr-2'
LLM_MY_TRANSLATE_MODEL='translategemma-12b-it'
LMS_BASE_URL='http://localhost:1234/v1'

abbrev-alias llm-heavy-model="lms chat '$LLM_MY_HEAVY_MODEL'"
abbrev-alias llm-default-model="lms chat '$LLM_MY_DEFAULT_MODEL'"
abbrev-alias llm-fast-model="lms chat '$LLM_MY_FAST_MODEL'"
abbrev-alias llm-vision-model="lms chat '$LLM_MY_VISION_MODEL'"
abbrev-alias How="noglob lms chat '$LLM_MY_DEFAULT_MODEL' --prompt 'I am using zsh on macOS. I want to ask how to perform following operations on console. Please respond with simple answer. How'"

# Translate text via LM Studio HTTP API
# Usage: llm-translate SOURCE_CODE TARGET_CODE [TEXT]
# Example: llm-translate en ja "Hello, world!"
# Example: echo "Hello" | llm-translate en ja
function llm-translate() {
	if [[ $# -lt 2 ]]; then
		echo "Usage: llm-translate SOURCE_CODE TARGET_CODE [TEXT]" >&2
		echo "Example: llm-translate en ja \"Hello, world!\"" >&2
		echo "Example: echo \"Hello\" | llm-translate en ja" >&2
		return 1
	fi
	local source_code="$1" target_code="$2" text
	if [[ $# -ge 3 ]]; then
		text="$3"
	else
		text=$(cat)
	fi
	if [[ -z "$text" ]]; then
		echo "Error: No input text provided" >&2
		return 1
	fi
	local -A lang_names=(
		en "English" ja "Japanese" ja-JP "Japanese"
		es "Spanish" fr "French" de "German"
		it "Italian" zh "Chinese" zh-TW "Chinese"
		zh-Hans "Chinese" zh-Hant "Chinese" ko "Korean"
	)
	local source_lang="${lang_names[$source_code]:-$source_code}"
	local target_lang="${lang_names[$target_code]:-$target_code}"
	local prompt="You are a professional ${source_lang} (${source_code}) to ${target_lang} (${target_code}) translator. Your goal is to accurately convey the meaning and nuances of the original ${source_lang} text while adhering to ${target_lang} grammar, vocabulary, and cultural sensitivities.
Produce only the ${target_lang} translation, without any additional explanations or commentary. Please translate the following ${source_lang} text into ${target_lang}:

${text}"
	local payload
	payload=$(python3 -c "import json,sys; print(json.dumps({'model': sys.argv[1], 'messages': [{'role': 'user', 'content': sys.argv[2]}]}))" \
		"$LLM_MY_TRANSLATE_MODEL" "$prompt")
	curl -s "$LMS_BASE_URL/chat/completions" \
		-H "Content-Type: application/json" \
		-d "$payload" | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
}

# OCR an image file via LM Studio HTTP API
# Usage: llm-ocr <image_file>
function llm-ocr() {
	local image_file="$1"
	if [[ -z "$image_file" ]]; then
		echo "Usage: llm-ocr <image_file>" >&2
		return 1
	fi
	if [[ ! -f "$image_file" ]]; then
		echo "File not found: $image_file" >&2
		return 1
	fi
	local b64
	b64=$(base64 -i "$image_file")
	local mime
	case "${image_file:e:l}" in
		jpg|jpeg) mime="image/jpeg" ;;
		png)      mime="image/png" ;;
		gif)      mime="image/gif" ;;
		webp)     mime="image/webp" ;;
		*)        mime="image/jpeg" ;;
	esac
	curl -s "$LMS_BASE_URL/chat/completions" \
		-H "Content-Type: application/json" \
		-d "{
			\"model\": \"$LLM_MY_OCR_MODEL\",
			\"messages\": [{
				\"role\": \"user\",
				\"content\": [
					{\"type\": \"image_url\", \"image_url\": {\"url\": \"data:$mime;base64,$b64\"}},
					{\"type\": \"text\", \"text\": \"Please perform OCR on this image and output all text exactly as it appears.\"}
				]
			}]
		}" | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
}
