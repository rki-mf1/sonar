#!/usr/bin/env bash

./scripts/linux/dc-dev.sh run --rm sonar-backend python ./manage.py "$@"
