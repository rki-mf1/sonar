#!/usr/bin/env bash

docker compose -f docker-compose-dev.yml exec -T dev-django pip install --no-cache-dir --disable-pip-version-check -r requirements-testing.txt
docker compose -f docker-compose-dev.yml exec -T dev-django coverage run ./manage.py test --no-input "$@"
