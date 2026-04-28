# Sonar GHCR Deployment Bundle

This directory contains the example configuration set for running sonar directly
from prebuilt container images.

## Files

- `.env.example`: image tags and published host ports used by `compose.yml`
- `backend.env.example`: non-secret backend settings
- `backend.secrets.env.example`: secret values you must replace
- `frontend.env.example`: frontend runtime configuration
- `sonar-cli.sh`: helper script for running the published CLI container
- `sonar-cli.config.example`: example CLI configuration for the deploy bundle
- `compose.yml`: image-based deployment example

## Quick Start

For the fastest end-to-end setup, use the bootstrap script:

```sh
./bootstrap.sh --tag latest
```

This script:

- creates active config files from the `*.example` templates if needed
- preserves existing config files unless you pass `--force`
- updates the active `.env` file to use the requested backend, frontend, and CLI image tag
- writes the active `sonar-cli.config` to the example-deploy backend API URL
- pulls the latest images for that tag
- starts the stack and runs the smoke test
- downloads the example datasets
- runs the documented SARS-CoV-2 and Mpox CLI example commands

Useful options:

```sh
./bootstrap.sh --tag v1.2.3
./bootstrap.sh --tag latest --force
```

1. Copy the example files:

   ```sh
   cp .env.example .env
   cp backend.env.example backend.env
   cp backend.secrets.env.example backend.secrets.env
   cp frontend.env.example frontend.env
   cp sonar-cli.config.example sonar-cli.config
   ```

2. Replace the secret values in `backend.secrets.env`.

3. If you are deploying anywhere other than your local machine, update:
   - `ALLOWED_HOSTS` in `backend.env`
   - `CORS_ALLOWED_ORIGINS` in `backend.env`
   - `SONAR_FRONTEND_BACKEND_ADDRESS` in `frontend.env`

4. Start the stack:

   ```sh
   docker compose up -d
   ```

5. Access the services:
   - frontend: `http://localhost:18080`
   - backend API: `http://localhost:18000/api/`

Port roles in this example:

- `18080`: public frontend port published from the frontend container
- `18000`: public backend API port published from the backend container
- `80`: frontend container internal port
- `9080`: backend container internal app-server port

## Fresh-Setup Smoke Test

Run these checks from inside `example-deploy/` after creating the env files:

```sh
docker compose config -q
docker compose up -d
docker compose ps
docker compose exec -T sonar-backend \
  curl --fail http://127.0.0.1:9080/api/database/get_database_tables_status/
```

If `docker compose up -d` fails with an error like
`ghcr.io/rki-mf1/sonar-backend:latest ... denied`, your environment cannot pull
the published GHCR images. In practice that means one of these is true:

- you need to authenticate first with `docker login ghcr.io`
- the package is not publicly pullable, so this bundle cannot currently be used
  by an unauthenticated new user

## Example Data Setup

The deploy bundle itself does not include datasets. For a quick trial, either:

- clone the repository and mount `../test-data`
- or download a few small public/example files into `example-deploy/data`

The commands below use a local `data/` directory so they work with the release
bundle as well.

The CLI is intentionally not part of the `compose.yml` stack. It is meant to
run separately and talk to the backend over its HTTP API, including from a
different machine.

### Download Small Test Datasets

```sh
mkdir -p data/sars-cov-2 data/mpox

curl -L -o data/sars-cov-2/MN908947.nextclade.gb \
  https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/sars-cov-2/MN908947.nextclade.gb
curl -L -o data/sars-cov-2/SARS-CoV-2_12.fasta.xz \
  https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/sars-cov-2/SARS-CoV-2_12.fasta.xz
curl -L -o data/sars-cov-2/SARS-CoV-2_12.tsv.xz \
  https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/sars-cov-2/SARS-CoV-2_12.tsv.xz
curl -L -o data/sars-cov-2/lineages_test.tsv \
  https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/sars-cov-2/lineages_test.tsv

curl -L -o data/mpox/clade-IIb-NC_063383.1.gb \
  https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/mpox/clade-IIb-NC_063383.1.gb
curl -L -o data/mpox/mpox_2.fasta.xz \
  https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/mpox/mpox_2.fasta.xz
curl -L -o data/mpox/mpox_2.tsv \
  https://raw.githubusercontent.com/rki-mf1/sonar/main/test-data/mpox/mpox_2.tsv
```

### Update CLI Image

```sh
set -a
. ./.env
set +a

docker pull "$SONAR_CLI_IMAGE"
```

### Prepare the CLI Config

```sh
cp sonar-cli.config.example sonar-cli.config
```

Then uncomment and adjust `API_URL` in `sonar-cli.config` if you changed the
published backend port. The default example value is `http://127.0.0.1:18000/api`.

If you want to persist the same config outside the bundle, copy it to:

```sh
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/sonar-cli"
cp sonar-cli.config "${XDG_CONFIG_HOME:-$HOME/.config}/sonar-cli/sonar-cli.config"
```

### Reusable CLI Helper

Use the provided script:

```sh
./sonar-cli.sh list-ref
```

`sonar-cli.sh`:

- mounts `data/` into the container
- prefers the local `sonar-cli.config` file when present
- otherwise falls back to the host XDG config file if `~/.config/sonar-cli/sonar-cli.config` exists
- otherwise falls back to `API_URL=http://127.0.0.1:18000/api`
- uses `ghcr.io/rki-mf1/sonar-cli:latest` by default, or `SONAR_CLI_IMAGE=...` if you override it explicitly

For a local deployment on Linux, `sonar-cli.sh` uses `--network host` so the CLI
container can reach the backend at `127.0.0.1:18000` without joining the
compose network. The bootstrap script uses the same approach, so it currently
assumes a Linux host with Docker and `docker compose` available.

### Minimal SARS-CoV-2 Dataset

```sh
./sonar-cli.sh add-ref --gb /data/sars-cov-2/MN908947.nextclade.gb

# Optional but useful for SARS-CoV-2 sublineage queries.
./sonar-cli.sh import-lineage -l /data/sars-cov-2/lineages_test.tsv

./sonar-cli.sh import \
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
```

Basic checks:

```sh
./sonar-cli.sh list-ref
./sonar-cli.sh info
./sonar-cli.sh match -r MN908947.3 --count
```

### Minimal Mpox Dataset

```sh
./sonar-cli.sh add-ref --gb /data/mpox/clade-IIb-NC_063383.1.gb

./sonar-cli.sh import \
  -r NC_063383.1 \
  --auto-anno \
  --fasta /data/mpox/mpox_2.fasta.xz \
  --tsv /data/mpox/mpox_2.tsv \
  --cols name=name
```

Basic checks:

```sh
./sonar-cli.sh list-ref
./sonar-cli.sh info
./sonar-cli.sh match -r NC_063383.1 --count
```

## Updating Images

Update the image tags in `.env`, then run:

```sh
docker compose pull
docker compose up -d
```

## Persistent Data

This example stores persistent data in Docker named volumes:

- `sonar-postgres`
- `sonar-data`
- `sonar-logs`

Switch these to bind mounts if you want host-managed storage.
