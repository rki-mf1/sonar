#!/bin/bash

docker compose --env-file conf/docker/common.env --env-file conf/docker/prod.env --env-file conf/docker/prod-secrets.env "$@"
