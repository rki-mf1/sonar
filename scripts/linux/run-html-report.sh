#!/usr/bin/env bash

set -e

docker compose -f docker-compose-dev.yml exec -T dev-django coverage report "$@"
docker compose -f docker-compose-dev.yml exec -T dev-django coverage html "$@"
xdg-open htmlcov/index.html
