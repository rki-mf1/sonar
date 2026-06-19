# Sonar Docker Deployment

This directory contains a Docker Compose deployment for running Sonar from
prebuilt Docker images. It is the recommended setup for users who want to try or
operate Sonar without cloning or building the source repository.

Release builds publish this directory as `sonar-docker-deploy-bundle.tar.gz` on
[GitHub Releases](https://github.com/rki-mf1/sonar/releases). Download and
extract it:

```sh
curl -LO https://github.com/rki-mf1/sonar/releases/latest/download/sonar-docker-deploy-bundle.tar.gz
tar -xzf sonar-docker-deploy-bundle.tar.gz
cd example-deploy
```

The stack includes:

- backend API
- frontend web interface
- PostgreSQL database
- Redis cache and worker broker
- backend worker services

The CLI is run separately through `sonar-cli.sh` so it can be used for imports,
queries, and automation from the host.

## Files

| File | Purpose |
| --- | --- |
| `.env.example` | Docker image tags and published host ports. |
| `backend.env.example` | Non-secret backend settings. |
| `backend.secrets.env.example` | Secret values that must be unique per deployment. |
| `frontend.env.example` | Frontend runtime configuration. |
| `sonar-cli.config.example` | Example CLI configuration for this deployment. |
| `sonar-cli.sh` | Helper for running the published CLI Docker image. |
| `compose.yml` | Docker Compose stack. |

Active files without `.example` are local deployment files. They should not be
committed.

## Quick Start

Requirements:

- Docker Engine with Docker Compose plugin
- `curl`
- `python3`

Run:

```sh
./bootstrap.sh --tag latest
```

The bootstrap script:

- creates active config files from templates when they do not exist
- preserves existing config unless `--force` is passed
- generates local secret defaults when needed
- sets backend, frontend, and CLI Docker image tags
- pulls the Docker images
- validates and starts the Compose stack
- downloads small SARS-CoV-2 and Mpox example datasets
- runs documented CLI example imports

Useful variants:

```sh
./bootstrap.sh --tag v1.2.3
./bootstrap.sh --tag latest --force
```

Use a fixed release tag for production. Use `latest` only for evaluation or
intentional tracking of the newest published image.

## Service URLs

Default published ports:

| Service | Default URL | Config |
| --- | --- | --- |
| Frontend | `http://localhost:18080` | `SONAR_PUBLIC_FRONTEND_PORT` in `.env` |
| Backend API | `http://localhost:18000/api/` | `SONAR_PUBLIC_BACKEND_PORT` in `.env` |
| Django admin | `http://localhost:18000/admin/` | same backend port |

Container-internal ports:

| Port | Role |
| --- | --- |
| `80` | frontend container web server |
| `9080` | backend app server |

## Manual Setup

If you do not use `bootstrap.sh`, create config files manually:

```sh
cp .env.example .env
cp backend.env.example backend.env
cp backend.secrets.env.example backend.secrets.env
cp frontend.env.example frontend.env
cp sonar-cli.config.example sonar-cli.config
```

Then:

1. Replace all secret values in `backend.secrets.env`.
2. If deploying anywhere other than localhost, update:
   - `ALLOWED_HOSTS` in `backend.env`
   - `CORS_ALLOWED_ORIGINS` in `backend.env`
   - `SONAR_FRONTEND_BACKEND_ADDRESS` in `frontend.env`
3. Start the stack:

```sh
docker compose pull
docker compose config -q
docker compose up -d
docker compose ps
```

Smoke test:

```sh
docker compose exec -T sonar-backend \
  curl --fail http://127.0.0.1:9080/api/database/get_database_tables_status/
```

If image pulls fail with an access error, authenticate with:

```sh
docker login ghcr.io
```

If the packages are not publicly pullable in your environment, unauthenticated
Docker deployment will not work until access is fixed.

## Configuration

### `.env`

Controls Docker image names and published ports.

Important settings:

| Setting | Purpose |
| --- | --- |
| `SONAR_BACKEND_IMAGE` | Backend Docker image and tag. |
| `SONAR_FRONTEND_IMAGE` | Frontend Docker image and tag. |
| `SONAR_CLI_IMAGE` | CLI Docker image and tag used by `sonar-cli.sh`. |
| `SONAR_PUBLIC_BACKEND_PORT` | Host port for the backend API. |
| `SONAR_PUBLIC_FRONTEND_PORT` | Host port for the frontend. |

### `backend.env`

Contains non-secret backend configuration such as allowed hosts, CORS origins,
batch sizes, logging, and worker/runtime behavior.

### `backend.secrets.env`

Contains deployment secrets. Replace generated or example values before any
real deployment.

At minimum, set:

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `CELERY_FLOWER_AUTH`, if worker monitoring is exposed in your environment

### `frontend.env`

Controls frontend runtime behavior. The most important setting is:

```sh
SONAR_FRONTEND_BACKEND_ADDRESS=http://localhost:18000/api/
```

Set this to the backend API URL that browsers should use.

## CLI Helper

The CLI is intentionally not a long-running Compose service. Run it with:

```sh
./sonar-cli.sh reference list
```

The helper:

- runs the published CLI Docker image
- mounts `data/` into the CLI container as `/data`
- prefers local `sonar-cli.config`
- falls back to host XDG config if present
- otherwise uses `API_URL=http://127.0.0.1:18000/api`
- uses `SONAR_CLI_IMAGE` when set

On Linux, the helper uses host networking so the CLI container can reach the
backend at `127.0.0.1:18000`.

## Example Data

The deployment bundle does not include datasets. The bootstrap script downloads
small examples into `data/`. To download them manually:

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

## Minimal SARS-CoV-2 Workflow

```sh
./sonar-cli.sh reference add --genbank /data/sars-cov-2/MN908947.nextclade.gb

./sonar-cli.sh lineage import -l /data/sars-cov-2/lineages_test.tsv

./sonar-cli.sh sample import \
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

Check the result:

```sh
./sonar-cli.sh reference list
./sonar-cli.sh info show
./sonar-cli.sh sample match -r MN908947.3 --count
```

## Minimal Mpox Workflow

```sh
./sonar-cli.sh reference add --genbank /data/mpox/clade-IIb-NC_063383.1.gb

./sonar-cli.sh sample import \
  -r NC_063383.1 \
  --auto-anno \
  --fasta /data/mpox/mpox_2.fasta.xz \
  --tsv /data/mpox/mpox_2.tsv \
  --cols name=name
```

Check the result:

```sh
./sonar-cli.sh reference list
./sonar-cli.sh info show
./sonar-cli.sh sample match -r NC_063383.1 --count
```

## Updating

Change image tags in `.env`, then run:

```sh
docker compose pull
docker compose up -d
```

For production, update to a specific release tag and keep a copy of the previous
working `.env` so rollback is straightforward.

## Stopping

Stop services:

```sh
docker compose down
```

Stop services and remove volumes only when you intentionally want to delete local
database state:

```sh
docker compose down -v
```
