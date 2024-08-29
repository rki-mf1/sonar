#!/usr/bin/env bash

set -euo pipefail

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"

# Default to adding test data and also rebuilding the docker container
DELETE=1
REBUILD=0
TEST_DATA=0

# Helper function to print help to stderr.
help()
{
  >&2 echo "Build a clean production environment"
  >&2 echo ""
  >&2 echo "./scripts/linux/build-prod-env.sh [-r] [-t]"
  >&2 echo ""
  >&2 echo "  -d : delete current ./work directory containing mapped directories [default: disabled]"
  >&2 echo "  -r : *disable* rebuilding docker container [default: rebuilding enabled]"
  >&2 echo "  -t : *disable* adding test data [default: adding test data enabled]"
}

# Parse command line arguments into bash variables.
while getopts "hdrt" arg; do
  case $arg in
    h)
      help
      exit 0
      ;;
    d)
      # Enable the deletion of ./work dir
      DELETE=0
      ;;
    r)
      # Disable rebuilding the docker container
      REBUILD=1
      ;;
    t)
      # Disable adding test data
      TEST_DATA=1
      ;;
  esac
done

$SCRIPTPATH/dc-prod.sh down -v

if [ $DELETE -eq 0 ]; then
  rootlesskit rm -rf ./work
fi

DC_ARGS=""
if [ $REBUILD -eq 0 ]; then
  $SCRIPTPATH/build-docker-dev.sh
  DC_ARGS="--build"
fi

$SCRIPTPATH/dc-prod.sh up -d $DC_ARGS
$SCRIPTPATH/prod-manage.sh migrate

if [ $TEST_DATA -eq 0 ]; then
  $SCRIPTPATH/prod-manage.sh loaddata initial_auth test_data_sm
else
  $SCRIPTPATH/prod-manage.sh loaddata initial_auth
fi

# This is a hack to resolve the annoying apserver log messages
$SCRIPTPATH/dc-prod.sh restart sonar-django-apscheduler
