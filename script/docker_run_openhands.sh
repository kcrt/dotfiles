#!/bin/sh

# Run the OpenHands app in a Docker container
# ./docker_run_openhands.sh <llm> <sandbox-runtime>
# llm - the name of the LLM to use: "claude:claude3.5"(default), "openai:gpt-4o", "ollama:<name>"
# sandbox-runtime - default is runtime:0.18-nikolaik

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
