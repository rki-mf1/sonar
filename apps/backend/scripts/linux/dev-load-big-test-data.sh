#!/usr/bin/env bash

./scripts/linux/dev-manage.sh flush --noinput
./scripts/linux/dev-manage.sh loaddata initial_auth test_data_1000
./scripts/linux/dev-copy-gbk.sh ../../../test-data/covid19/MN908947.nextclade.gb ./work/sonar/data/import/gbks/
