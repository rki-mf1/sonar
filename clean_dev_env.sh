#!/bin/bash

NoTestData=false
NoRebuild=false

while getopts ":nr" opt; do
  case $opt in
    n)
      NoTestData=true
      ;;
    r)
      NoRebuild=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      ;;
  esac
done

shift $((OPTIND -1))

bash dc-dev.sh down
if [ $? -ne 0 ]; then
    exit $?
fi

if [ "$NoRebuild" = true ]; then
    echo "######### Skip rebuilding the docker image ###########"
else
    ./build_docker_dev.sh
    if [ $? -ne 0 ]; then
        exit $?
    fi
fi

bash dc-dev.sh up -d
if [ $? -ne 0 ]; then
    exit $?
fi

bash dev-manage.sh migrate
if [ $? -ne 0 ]; then
    exit $?
fi

if [ "$NoTestData" = true ]; then
    echo "######### loading fixtures without test data #########"
    bash dev-manage.sh loaddata initial_auth
else
    echo "######### loading fixtures with test data ############"
    bash dev-manage.sh loaddata initial_auth test_data
fi

if [ $? -ne 0 ]; then
    exit $?
fi
