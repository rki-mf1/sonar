#!/usr/bin/env bash

set -e

CONDA_ENV="sonar-cli"

echo "Make sure you do 'git pull' to update the code before running this command."

conda env update -n "$CONDA_ENV" --prune
conda run -n "$CONDA_ENV" poetry install --only main
conda run -n "$CONDA_ENV" pip install git+https://git@github.com/kcleal/pywfa.git@9c5e192
echo "Update complete. Testing to see if we can access the backend..."
conda run -n "$CONDA_ENV" sonar-cli list-ref
