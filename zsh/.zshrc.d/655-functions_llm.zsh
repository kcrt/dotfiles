#
#	655-functions_llm.zsh
#		LLM (LM Studio) functions and configuration
#

LLM_MY_DEFAULT_MODEL='google/gemma-4-12b-qat'
LLM_MY_HEAVY_MODEL='orcarouter/qwen3.8-27b-uncensored'
# LFM3-Omni-2B (Q4_K_M + mmproj) は文章と画像の両方を扱える軽量モデル。
# 画像の説明は gemma-4-12b より正確で速かったが、シェルの質問 (How) や知識を問う解説・
# 一字一句の OCR は誤りが混ざるので、それぞれ DEFAULT / OCR に任せる
LLM_MY_FAST_MODEL='lfm3-omni-2b'
LLM_MY_VISION_MODEL='lfm3-omni-2b'
LLM_MY_OCR_MODEL='deepseek-ocr-2'
# pfnet/plamo-3-translate-2b-GGUF (Q4_K_M)。翻訳専用で、言語はシステムメッセージの設定ブロックで渡す
LLM_MY_TRANSLATE_MODEL='plamo-3-translate-2b'
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
	# PLaMo の言語コードは小文字・地域なし (ja, en, zh-hans, zh-hant)
	local -A lang_codes=(
		ja-jp ja en-us en en-gb en
		zh zh-hans zh-cn zh-hans zh-tw zh-hant
	)
	source_code="${(L)source_code}"
	target_code="${(L)target_code}"
	source_code="${lang_codes[$source_code]:-$source_code}"
	target_code="${lang_codes[$target_code]:-$target_code}"
	# チャットテンプレートが読む設定ブロック。target_lang が無いと訳先が ja に固定される
	local settings="[plamo-translate]
source_lang=${source_code}
target_lang=${target_code}
---"
	local payload
	payload=$(python3 -c "import json,sys; print(json.dumps({'model': sys.argv[1], 'temperature': 0, 'messages': [{'role': 'system', 'content': sys.argv[2]}, {'role': 'user', 'content': sys.argv[3]}]}))" \
		"$LLM_MY_TRANSLATE_MODEL" "$settings" "$text")
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
			\"reasoning_effort\": \"none\",
			\"messages\": [{
				\"role\": \"user\",
				\"content\": [
					{\"type\": \"image_url\", \"image_url\": {\"url\": \"data:$mime;base64,$b64\"}},
					{\"type\": \"text\", \"text\": \"Please perform OCR on this image and output all text exactly as it appears.\"}
				]
			}]
		}" | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
}
