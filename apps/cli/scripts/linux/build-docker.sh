#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO_ROOT="$(cd "$APP_DIR/../.." && pwd)"
SONAR_VERSION="$(tr -d '[:space:]' < "$REPO_ROOT/VERSION")"

docker build --build-arg "SONAR_VERSION=$SONAR_VERSION" --tag sonar-cli:local --file "$APP_DIR/Dockerfile" "$APP_DIR"
