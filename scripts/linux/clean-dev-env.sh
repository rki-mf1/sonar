#!/usr/bin/env bash

set -euo pipefail

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"

# Default to adding test data and also rebuilding the docker container
REBUILD=0
TEST_DATA=0

# Helper function to print help to stderr.
help()
{
  >&2 echo "Build a clean dev environment"
  >&2 echo ""
  >&2 echo "./scripts/linux/build-dev-env.sh [-r] [-t]"
  >&2 echo ""
  >&2 echo "  -r : *disable* rebuilding docker container [default: rebuilding enabled]"
  >&2 echo "  -t : *disable* adding test data [default: adding test data enabled]"
}

# Parse command line arguments into bash variables.
while getopts "hrt" arg; do
  case $arg in
    h)
      help
      exit 0
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

$SCRIPTPATH/dc-dev.sh down -v

DC_ARGS=""
if [ $REBUILD -eq 0 ]; then
  $SCRIPTPATH/build-docker-dev.sh
  DC_ARGS="--build"
fi

$SCRIPTPATH/dc-dev.sh up -d $DC_ARGS
$SCRIPTPATH/dev-manage.sh migrate

if [ $TEST_DATA -eq 0 ]; then
  $SCRIPTPATH/dev-manage.sh loaddata initial_auth test_data_sm
else
  $SCRIPTPATH/dev-manage.sh loaddata initial_auth
fi
