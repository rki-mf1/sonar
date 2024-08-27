#!/usr/bin/env bash

./scripts/linux/dc-dev.sh run --rm sonar-django-backend "poetry run python ./manage.py $*"
