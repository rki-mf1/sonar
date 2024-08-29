#!/usr/bin/env bash

./scripts/linux/dc-prod.sh run --rm sonar-django-backend "poetry run python ./manage.py $*"
