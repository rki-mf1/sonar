#!/bin/bash

docker build --network=host -t backend_dev:local -f ./Dockerfile .

# alternative docker command
# docker build -t backend_dev:local -f ./Dockerfile .
