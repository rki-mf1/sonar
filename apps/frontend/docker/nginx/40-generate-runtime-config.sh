#!/bin/sh
set -eu

: "${SONAR_FRONTEND_BACKEND_ADDRESS:=http://localhost:8000/api/}"
: "${SONAR_FRONTEND_AUTH_TOKEN:=}"

envsubst '${SONAR_FRONTEND_BACKEND_ADDRESS} ${SONAR_FRONTEND_AUTH_TOKEN}' \
  < /usr/share/nginx/html/runtime-config.js.template \
  > /usr/share/nginx/html/runtime-config.js
