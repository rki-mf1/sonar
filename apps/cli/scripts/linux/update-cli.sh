#!/usr/bin/env bash

set -e

CONDA_ENV="sonar-cli"

echo "Make sure you do 'git pull' to update the code before running this command."

conda env update -n "$CONDA_ENV" --prune
echo "Update complete. Testing to see if we can access the backend..."
conda run -n "$CONDA_ENV" uv run sonar-cli list-ref
