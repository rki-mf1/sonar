#!/usr/bin/env bash

set -e

scripts/linux/dc-dev.sh exec -T sonar-backend coverage report "$@"
scripts/linux/dc-dev.sh exec -T sonar-backend coverage html "$@"
xdg-open htmlcov/index.html
