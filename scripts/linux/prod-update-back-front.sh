#!/usr/bin/env bash

set -e

echo "Building the frontend"
cd apps/frontend
conda update -n sonar-frontend --yes nodejs
conda run -n sonar-frontend npm install
conda run -n sonar-frontend npm run build-only
cd -

echo "Rebuilding and restarting the frontend"
cd apps/backend
./scripts/linux/dc-prod.sh down --remove-orphans
./scripts/linux/build-docker-dev.sh
./scripts/linux/dc-prod.sh up --force-recreate -d
