#!/bin/sh

# Run the OpenHands app in a Docker container
# ./docker_run_openhands.sh <llm> <sandbox-runtime>
# llm - the name of the LLM to use: "claude:claude3.5"(default), "openai:gpt-4o", "ollama:<name>"
# sandbox-runtime - default is runtime:0.18-nikolaik (Note: script currently hardcodes a newer version)

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Runs the OpenHands application in a Docker container."
    echo "This script currently uses a hardcoded SANDBOX_RUNTIME: docker.all-hands.dev/all-hands-ai/runtime:0.21-nikolaik"
    echo "It maps port 3000, mounts ~/.openhands-state, and shares the Docker socket."
    echo ""
    echo "Environment variables like LLM_API_KEY (e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY) should be set in your environment"
    echo "if you intend to use specific LLMs with OpenHands that require them."
    echo "The script previously had commented-out logic for LLM and SANDBOX_RUNTIME parameters,"
    echo "but these are not currently active."
    exit 0
fi

# check parameters
# if [ -z "$1" ]; then
#     echo "No LLM specified, using claude:claude3.5"
#     LLM=claude:claude3-5-sonnet
# else
#     LLM=$1
# fi
# 
# if [ -z "$2" ]; then
#     echo "No sandbox-runtime specified, using runtime:0.18-nikolaik"
#     SANDBOX_RUNTIME=docker.all-hands.dev/all-hands-ai/runtime:0.18-nikolaik
# else
#     SANDBOX_RUNTIME=$2
# fi

SANDBOX_RUNTIME=docker.all-hands.dev/all-hands-ai/runtime:0.21-nikolaik

docker pull $SANDBOX_RUNTIME
docker run -it --rm --pull=always \
    -e SANDBOX_RUNTIME_CONTAINER_IMAGE=$SANDBOX_RUNTIME \
    -e LOG_ALL_EVENTS=true \
    -e LLM_RETRY_MULTIPLIER=4 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v ~/.openhands-state:/.openhands-state \
    -p 3000:3000 \
    --add-host host.docker.internal:host-gateway \
    --name openhands-app \
    docker.all-hands.dev/all-hands-ai/openhands:0.21
