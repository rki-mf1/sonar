#!/bin/bash
bash dev-manage.ps1 flush --noinput
bash dev-manage.ps1 loaddata initial_auth test_data_big