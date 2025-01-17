#!/usr/bin/env bash

./scripts/linux/dev-manage.sh flush --noinput
./scripts/linux/dev-manage.sh loaddata initial_auth test_data_10k
./scripts/linux/dev-copy-gbk.sh test-data/MN908947.nextclade.gb ./work/sonar/data/import/gbks/
