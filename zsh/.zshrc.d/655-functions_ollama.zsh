#
#	655-functions_ollama.zsh
#		Ollama functions and configuration
#
#
export OLLAMA_NUM_CTX=8192

OLLAMA_MY_HEAVY_MODEL='gemma3:27b-it-qat'
OLLAMA_MY_DEFAULT_MODEL='gemma3:12b-it-qat'
OLLAMA_MY_FAST_MODEL='gemma3:4b-it-qat'
OLLAMA_MY_VISION_MODEL='qwen3-vl:latest'
OLLAMA_MY_OCR_MODEL='deepseek-ocr:latest'
OLLAMA_MY_DRAW_MODEL='x/z-image-turbo:latest'

abbrev-alias ollama-update="ollama list | tail -n +2 | tr -s ' ' | cut -d ' ' -f1 | xargs -n1 ollama pull"
abbrev-alias ollama-heavy-model="ollama run $OLLAMA_MY_HEAVY_MODEL"
abbrev-alias ollama-default-model="ollama run $OLLAMA_MY_DEFAULT_MODEL"
abbrev-alias ollama-fast-model="ollama run $OLLAMA_MY_FAST_MODEL"
abbrev-alias ollama-vision-model="ollama run $OLLAMA_MY_VISION_MODEL Please describe the image:"
abbrev-alias ollama-ocr-model="ollama run $OLLAMA_MY_OCR_MODEL"
abbrev-alias ollama-draw="ollama run $OLLAMA_MY_DRAW_MODEL"
abbrev-alias How="noglob ollama run $OLLAMA_MY_DEFAULT_MODEL 'I am using zsh on macOS. I want to ask how to perform following operations on console. Please respond with simple answer. How'"
