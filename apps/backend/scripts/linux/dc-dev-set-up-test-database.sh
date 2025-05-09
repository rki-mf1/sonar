#!/bin/bash

docker compose -f compose.yml -f compose-dev.yml --env-file conf/docker/common.env --env-file conf/docker/sonar-cli-action.env --env-file conf/docker/dev-secrets.env "$@"

# Terminate all active connections to the database
docker exec -it sonar-db psql -h localhost -p 8432 -U postgres -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'sonar-test' AND pid <> pg_backend_pid();"

# Drop and recreate the database
docker exec -it sonar-db psql -h localhost -p 8432 -U postgres -c 'DROP DATABASE IF EXISTS "sonar-test";'
docker exec -it sonar-db psql -h localhost -p 8432 -U postgres -c 'CREATE DATABASE "sonar-test";'

# Copy the dump file to the container
docker cp conf/initdb-test/dump-sonar-12-test-db.sql sonar-db:/dump-sonar-12-test-db.sql
# Restore the dump file into the database
docker exec -it sonar-db psql -h localhost -p 8432 -U postgres -d sonar-test -f /dump-sonar-12-test-db.sql
