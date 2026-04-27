#!/usr/bin/env bash

./scripts/linux/dc-prod.sh run --rm sonar-backend python ./manage.py "$@"
