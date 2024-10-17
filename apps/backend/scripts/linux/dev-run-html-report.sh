#!/usr/bin/env bash

set -e

scripts/linux/dc-dev.sh exec -T sonar-django-backend coverage report "$@"
scripts/linux/dc-dev.sh exec -T sonar-django-backend coverage html "$@"
xdg-open htmlcov/index.html
