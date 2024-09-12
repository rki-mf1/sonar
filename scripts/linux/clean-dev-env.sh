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
  >&2 echo "Build a clean dev environment"
  >&2 echo ""
  >&2 echo "./scripts/linux/build-dev-env.sh [-d] [-r] [-t]"
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

$SCRIPTPATH/dc-dev.sh down -v --remove-orphans

if [ $DELETE -eq 0 ]; then
  TRUE_DIR=$(realpath ./work)
  echo "You are about to delete the directory: '$TRUE_DIR'."
  read -p "Are you sure you want to do this? [yn]" -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo rm -rf ./work
  fi
fi

DC_ARGS=""
if [ $REBUILD -eq 0 ]; then
  $SCRIPTPATH/build-docker-dev.sh
  DC_ARGS="--build"
fi

$SCRIPTPATH/dc-dev.sh up -d $DC_ARGS
$SCRIPTPATH/dev-manage.sh migrate

if [ $TEST_DATA -eq 0 ]; then
  $SCRIPTPATH/dev-manage.sh loaddata initial_auth test_data_sm
  $SCRIPTPATH/dev-manage.sh import_lineage
else
  $SCRIPTPATH/dev-manage.sh loaddata initial_auth
fi

# This is a hack to resolve the annoying apserver log messages
$SCRIPTPATH/dc-dev.sh restart sonar-django-apscheduler
