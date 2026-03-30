#!/bin/sh

#===============================================================================
#
#          FILE:  test-ollama-models.sh
#
#         USAGE:  ./test-ollama-models.sh
#
#   DESCRIPTION:  Test all installed Ollama models with a sample prompt
#
#       OPTIONS:  ---
#  REQUIREMENTS:  ollama
#          BUGS:  ---
#         NOTES:  ---
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#      REVISION:  $Id$
#
#===============================================================================

set -e

cleanup() {
    if [ -n "$ollama_pid" ]; then
        kill "$ollama_pid" 2>/dev/null || true
    fi
    exit 130
}

trap cleanup INT TERM

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Test all installed Ollama models with a sample prompt.

OPTIONS:
    --help              Show this help message
    --prompt=TEXT       Custom prompt to test models with
                        (default: "Write a haiku about programming.")
    --more-prompts      Run with multiple predefined prompts:
                        1. Default prompt (haiku about programming)
                        2. Complex reasoning task
                        3. Food allergy medical question
                        4. Japanese local culture question

EXAMPLES:
    $(basename "$0")
    $(basename "$0") --prompt="Explain quantum computing in simple terms"
    $(basename "$0") --more-prompts

EOF
}

TEST_PROMPT="Write a haiku about programming."

while [ $# -gt 0 ]; do
    case $1 in
        --help)
            show_help
            exit 0
            ;;
        --prompt=*)
            TEST_PROMPT="${1#*=}"
            shift
            ;;
        --more-prompts)
            echo "Running with multiple prompts..."
            echo "=================================================="
            
            echo "1/4: Default prompt (haiku about programming)"
            "$0" --prompt="Write a haiku about programming."
            
            echo -e "\n\n2/4: Complex reasoning task"
            # この複雑な問題を解決してください：ある企業には、ウィジェットを製造する3つの工場があります。工場Aは1日あたり100個のウィジェットを製造し、不良率は5%です。工場Bは1日あたり150個のウィジェットを製造し、不良率は3%です。工場Cは1日あたり200個のウィジェットを製造し、不良率は2%です。企業が電力制約のため一度に1つの工場しか稼働できない場合、10,000個の不良品のないウィジェットを最短時間で納品するための最適な生産戦略は何か？
            "$0" --prompt="Solve this complex problem: A company has 3 factories producing widgets. Factory A produces 100 widgets per day with a 5% defect rate, Factory B produces 150 widgets per day with a 3% defect rate, and Factory C produces 200 widgets per day with a 2% defect rate. If the company needs to fulfill an order of 10,000 non-defective widgets in the shortest time possible, what is the optimal production strategy considering they can only operate one factory at a time due to power constraints?"
            
            echo -e "\n\n3/4: Food allergy medical question"
            "$0" --prompt="As an allergist-immunologist, explain the molecular mechanisms underlying IgE-mediated food allergies, including the role of cross-linking, mast cell degranulation, and the biphasic anaphylactic response. Discuss the current evidence for oral immunotherapy (OIT) versus epicutaneous immunotherapy (EPIT) in treating peanut allergies, and explain why some patients develop tolerance while others experience treatment-refractory severe reactions."
            
            echo -e "\n\n4/4: Japanese local culture question"
            "$0" --prompt="日本の「おもてなし」の文化について、その歴史的背景と現代社会における意義を説明してください。また、外国人観光客にとって「おもてなし」がどのような体験として感じられるのか、具体的な例を挙げて教えてください。"
            
            echo -e "\n\nAll multiple prompt testing completed!"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

echo "Testing all installed Ollama models..."
echo "Prompt: $TEST_PROMPT"
echo "======================================="

if ! command -v ollama >/dev/null 2>&1; then
    echo "Error: ollama is not installed or not in PATH"
    exit 1
fi

models=$(ollama list | awk 'NR>1 {print $1}')

if [ -z "$models" ]; then
    echo "No Ollama models found. Please install models first."
    exit 1
fi

for model in $models; do
    echo
    echo "Testing model: $model"
    echo "----------------------------------------"
    echo "Response:"
    
    start_time=$(date +%s)
    ollama run "$model" "$TEST_PROMPT" 2>/dev/null &
    ollama_pid=$!
    
    if wait "$ollama_pid"; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo "✓ $model completed in ${duration} seconds"
    else
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo "✗ $model failed after ${duration} seconds"
    fi
    
    ollama_pid=
    
    echo "========================================="
done

echo "All models tested."

