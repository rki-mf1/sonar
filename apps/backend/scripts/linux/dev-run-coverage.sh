#!/usr/bin/env bash

scripts/linux/dc-dev.sh exec -T sonar-backend pip install --no-cache-dir --disable-pip-version-check -r requirements-testing.txt
scripts/linux/dc-dev.sh exec -T sonar-backend coverage run ./manage.py test --no-input "$@"
