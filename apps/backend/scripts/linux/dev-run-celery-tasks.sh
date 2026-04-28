#!/usr/bin/env bash

scripts/linux/dc-dev.sh run --rm sonar-backend celery -A sonar_backend worker --loglevel=info --without-gossip --without-mingle --without-heartbeat -Ofair
