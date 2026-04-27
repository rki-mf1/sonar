#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SONAR_CLI_IMAGE="${SONAR_CLI_IMAGE:-ghcr.io/rki-mf1/sonar-cli:latest}"
SONAR_API_URL="${SONAR_API_URL:-http://127.0.0.1:18000/api}"
CLI_CONFIG_FILE="${CLI_CONFIG_FILE:-$SCRIPT_DIR/sonar-cli.config}"
HOST_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

cli_args=(
  --network host
  --volume "$PWD/data:/data:ro"
)

if [[ -f "$CLI_CONFIG_FILE" ]]; then
  cli_args+=(
    --env XDG_CONFIG_HOME=/config
    --volume "$CLI_CONFIG_FILE:/config/sonar-cli/sonar-cli.config:ro"
  )
elif [[ -f "$HOST_CONFIG_HOME/sonar-cli/sonar-cli.config" ]]; then
  cli_args+=(
    --env XDG_CONFIG_HOME=/host-config
    --volume "$HOST_CONFIG_HOME:/host-config:ro"
  )
else
  cli_args+=(
    --env API_URL="$SONAR_API_URL"
  )
fi

docker run --rm \
  "${cli_args[@]}" \
  "$SONAR_CLI_IMAGE" "$@"
