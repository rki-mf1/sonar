#!/bin/bash

docker compose -f compose.yml -f compose-dev.yml --env-file conf/docker/common.env --env-file conf/docker/dev.env --env-file conf/docker/dev-secrets.env "$@"
