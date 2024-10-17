#!/usr/bin/env bash

scripts/linux/dc-dev.sh run --rm sonar-django-backend celery -A covsonar_backend worker --loglevel=info --without-gossip --without-mingle --without-heartbeat -Ofair
