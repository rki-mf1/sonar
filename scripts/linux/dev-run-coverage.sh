#!/usr/bin/env bash

scripts/linux/dc-dev.sh exec -T sonar-django-backend pip install --no-cache-dir --disable-pip-version-check -r requirements-testing.txt
scripts/linux/dc-dev.sh exec -T sonar-django-backend coverage run ./manage.py test --no-input "$@"
