# Sonar GHCR Deployment Bundle

This directory contains the example configuration set for running sonar directly
from prebuilt container images.

## Files

- `.env.example`: image tags and published host ports used by `compose.yml`
- `backend.env.example`: non-secret backend settings
- `backend.secrets.env.example`: secret values you must replace
- `frontend.env.example`: frontend runtime configuration
- `compose.yml`: image-based deployment example

## Quick Start

1. Copy the example files:

   ```sh
   cp .env.example .env
   cp backend.env.example backend.env
   cp backend.secrets.env.example backend.secrets.env
   cp frontend.env.example frontend.env
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

### Define a Reusable CLI Helper

```sh
set -a
. ./.env
set +a

SONAR_API_URL="${SONAR_API_URL:-http://127.0.0.1:18000/api}"

run_cli() {
  docker run --rm \
    --network host \
    --env API_URL="$SONAR_API_URL" \
    --volume "$PWD/data:/data:ro" \
    "$SONAR_CLI_IMAGE" "$@"
}
```

For a local deployment on Linux, `--network host` lets the CLI container reach
the backend at `127.0.0.1:18000` without joining the compose network.

If the CLI runs on a different machine than the backend, use the same command
shape but point `SONAR_API_URL` at the remote backend, for example
`https://your-backend-host/api`.

### Minimal SARS-CoV-2 Dataset

```sh
run_cli add-ref --gb /data/sars-cov-2/MN908947.nextclade.gb

# Optional but useful for SARS-CoV-2 sublineage queries.
run_cli import-lineage -l /data/sars-cov-2/lineages_test.tsv

run_cli import \
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
run_cli list-ref
run_cli info
run_cli match -r MN908947.3 --count
```

### Minimal Mpox Dataset

```sh
run_cli add-ref --gb /data/mpox/clade-IIb-NC_063383.1.gb

run_cli import \
  -r NC_063383.1 \
  --auto-anno \
  --fasta /data/mpox/mpox_2.fasta.xz \
  --tsv /data/mpox/mpox_2.tsv \
  --cols name=name
```

Basic checks:

```sh
run_cli list-ref
run_cli info
run_cli match -r NC_063383.1 --count
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
