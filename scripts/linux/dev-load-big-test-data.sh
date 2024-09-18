#!/usr/bin/env bash

./scripts/linux/dev-manage.sh flush --noinput
./scripts/linux/dev-manage.sh loaddata initial_auth test_data_big
