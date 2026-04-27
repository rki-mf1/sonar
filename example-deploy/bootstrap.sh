#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

readonly DEFAULT_TAG="latest"
readonly BACKEND_REPO="ghcr.io/rki-mf1/sonar-backend"
readonly FRONTEND_REPO="ghcr.io/rki-mf1/sonar-frontend"
readonly CLI_REPO="ghcr.io/rki-mf1/sonar-cli"

TAG="$DEFAULT_TAG"
FORCE=0
SECRETS_WAS_COPIED=0

usage() {
  cat <<'EOF'
Usage: ./bootstrap.sh [--tag <tag>] [--force]

Initializes or refreshes the example-deploy bundle, pulls the requested image
tag, starts the stack, downloads example data, and runs the documented CLI
example commands.

Options:
  --tag <tag>   Docker image tag to use for backend, frontend, and CLI.
                Default: latest
  --force       Overwrite active config files from the *.example templates.
  -h, --help    Show this help text.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
  --tag)
    [[ $# -ge 2 ]] || {
      echo "Missing value for --tag" >&2
      exit 1
    }
    TAG="$2"
    shift 2
    ;;
  --force)
    FORCE=1
    shift
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown argument: $1" >&2
    usage >&2
    exit 1
    ;;
  esac
done

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

require_command docker
require_command curl
require_command python3

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is required." >&2
  exit 1
fi

copy_template_if_needed() {
  local src="$1"
  local dst="$2"

  if [[ $FORCE -eq 1 || ! -f "$dst" ]]; then
    cp "$src" "$dst"
    if [[ "$dst" == "backend.secrets.env" ]]; then
      SECRETS_WAS_COPIED=1
    fi
    echo "Wrote $(basename "$dst") from $(basename "$src")"
  else
    echo "Keeping existing $(basename "$dst")"
  fi
}

set_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"

  if grep -q "^${key}=" "$file"; then
    python3 - "$file" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text().splitlines()
updated = []
prefix = f"{key}="
replaced = False
for line in lines:
    if line.startswith(prefix) and not replaced:
        updated.append(f"{prefix}{value}")
        replaced = True
    else:
        updated.append(line)
if not replaced:
    updated.append(f"{prefix}{value}")
path.write_text("\n".join(updated) + "\n")
PY
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
}

random_hex() {
  python3 - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
}

ensure_secret_defaults() {
  local file="$1"
  local password flower secret_key

  password="$(random_hex)"
  secret_key="$(random_hex)"
  flower="admin:$(random_hex)"

  set_env_value "$file" "POSTGRES_PASSWORD" "$password"
  set_env_value "$file" "SECRET_KEY" "$secret_key"
  set_env_value "$file" "CELERY_FLOWER_AUTH" "$flower"
}

download_file() {
  local url="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"
  curl -fsSL "$url" -o "$dest"
}

copy_template_if_needed ".env.example" ".env"
copy_template_if_needed "backend.env.example" "backend.env"
copy_template_if_needed "backend.secrets.env.example" "backend.secrets.env"
copy_template_if_needed "frontend.env.example" "frontend.env"
copy_template_if_needed "sonar-cli.config.example" "sonar-cli.config"

if [[ $FORCE -eq 1 || $SECRETS_WAS_COPIED -eq 1 || ! -s backend.secrets.env ]]; then
  ensure_secret_defaults "backend.secrets.env"
fi

set_env_value ".env" "SONAR_BACKEND_IMAGE" "${BACKEND_REPO}:${TAG}"
set_env_value ".env" "SONAR_FRONTEND_IMAGE" "${FRONTEND_REPO}:${TAG}"
set_env_value ".env" "SONAR_CLI_IMAGE" "${CLI_REPO}:${TAG}"

set -a
. ./.env
set +a

set_env_value "sonar-cli.config" "API_URL" "http://127.0.0.1:${SONAR_PUBLIC_BACKEND_PORT}/api"

echo "Pulling stack images for tag: ${TAG}"
docker compose pull
docker pull "$SONAR_CLI_IMAGE"

echo "Validating compose configuration"
docker compose config -q

echo "Starting stack"
docker compose up -d --wait
docker compose ps

echo "Waiting for backend readiness"
docker compose exec -T sonar-backend \
  curl --fail http://127.0.0.1:9080/api/database/get_database_tables_status/

echo "Downloading example data"
download_file \
  "https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/sars-cov-2/MN908947.nextclade.gb" \
  "data/sars-cov-2/MN908947.nextclade.gb"
download_file \
  "https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/sars-cov-2/SARS-CoV-2_12.fasta.xz" \
  "data/sars-cov-2/SARS-CoV-2_12.fasta.xz"
download_file \
  "https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/sars-cov-2/SARS-CoV-2_12.tsv.xz" \
  "data/sars-cov-2/SARS-CoV-2_12.tsv.xz"
download_file \
  "https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/sars-cov-2/lineages_test.tsv" \
  "data/sars-cov-2/lineages_test.tsv"
download_file \
  "https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/mpox/clade-IIb-NC_063383.1.gb" \
  "data/mpox/clade-IIb-NC_063383.1.gb"
download_file \
  "https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/mpox/mpox_2.fasta.xz" \
  "data/mpox/mpox_2.fasta.xz"
download_file \
  "https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/mpox/mpox_2.tsv" \
  "data/mpox/mpox_2.tsv"

echo "Running CLI example commands"
SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh add-ref --gb /data/sars-cov-2/MN908947.nextclade.gb
SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh import-lineage -l /data/sars-cov-2/lineages_test.tsv
SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh import \
  -r MN908947.3 \
  --auto-anno \
  --fasta /data/sars-cov-2/SARS-CoV-2_12.fasta.xz \
  --tsv /data/sars-cov-2/SARS-CoV-2_12.tsv.xz \
  --cols \
  name=name \
  sequencing_reason=sequencing_reason \
  sample_type=sample_type \
  euro=euro \
  age=age \
  comments=comments \
  sequencing_tech=sequencing_tech \
  zip_code=zip_code \
  lab=lab \
  lineage=lineage \
  collection_date=collection_date
SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh list-ref
SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh info
SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh match -r MN908947.3 --count

SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh add-ref --gb /data/mpox/clade-IIb-NC_063383.1.gb
SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh import \
  -r NC_063383.1 \
  --auto-anno \
  --fasta /data/mpox/mpox_2.fasta.xz \
  --tsv /data/mpox/mpox_2.tsv \
  --cols name=name
SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh list-ref
SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh info
SONAR_CLI_IMAGE="$SONAR_CLI_IMAGE" ./sonar-cli.sh match -r NC_063383.1 --count

echo
echo "Bootstrap completed."
echo "Frontend: http://localhost:${SONAR_PUBLIC_FRONTEND_PORT}"
echo "Backend API: http://localhost:${SONAR_PUBLIC_BACKEND_PORT}/api/"
