#!/usr/bin/env bash

set -e

echo "Building the frontend"
cd apps/frontend
conda update -n sonar-frontend --yes nodejs
conda run -n sonar-frontend npm install
conda run -n sonar-frontend npm run build-only
cd -

FRONTEND_DIR=apps/backend/work/frontend/dist
echo "Installing the frontend (to $FRONTEND_DIR)"
mkdir -p "$FRONTEND_DIR"
rm -fr "$FRONTEND_DIR"/*
cp -r apps/frontend/dist/* "$FRONTEND_DIR"

echo "Rebuilding and restarting the frontend"
cd apps/backend
./scripts/linux/dc-prod.sh down --remove-orphans
./scripts/linux/build-docker-dev.sh
./scripts/linux/dc-prod.sh up --force-recreate -d
./scripts/linux/manage-prod.sh migrate
./scripts/linux/dc-prod.sh restart sonar-django-apscheduler
