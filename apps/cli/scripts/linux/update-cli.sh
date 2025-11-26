#!/usr/bin/env bash

set -e

CONDA_ENV="sonar-cli"

echo "Make sure you do 'git pull' to update the code before running this command."

conda env update -n "$CONDA_ENV" -f environment.yml --prune
conda run -n "$CONDA_ENV" poetry install --only main
echo "Update complete. Testing to see if we can access the backend..."
conda run -n "$CONDA_ENV" sonar-cli list-ref
