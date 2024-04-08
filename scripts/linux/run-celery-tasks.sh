#!/usr/bin/env bash

docker compose -f docker-compose-dev.yml run --rm dev-django celery -A covsonar_backend worker --loglevel=info --without-gossip --without-mingle --without-heartbeat -Ofair
