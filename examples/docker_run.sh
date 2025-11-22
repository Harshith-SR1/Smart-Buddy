#!/usr/bin/env bash
# Build and run Smart Buddy in Docker (Linux / macOS)
# Usage:
#   chmod +x examples/docker_run.sh
#   ./examples/docker_run.sh

IMAGE_NAME=smart-buddy:local
# Build image
docker build -t ${IMAGE_NAME} .
# Run, mounting local models directory so gpt4all models can be used
docker run --rm -it -v "$(pwd)/models:/app/models" ${IMAGE_NAME}
