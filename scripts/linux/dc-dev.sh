#!/bin/bash

docker compose --env-file conf/docker/common.env --env-file conf/docker/dev.env --env-file conf/docker/dev-secrets.env "$@"
