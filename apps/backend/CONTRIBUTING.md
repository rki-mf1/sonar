# Backend Contributing

This file covers source-based backend development. For user deployment, use the
Docker guide in [`../../example-deploy/README.md`](../../example-deploy/README.md).

## Requirements

- Docker with Docker Compose
- Python and Poetry for direct test/lint workflows
- A Unix-like shell for the Linux helper scripts

## Development Stack

From the repository root:

```sh
./apps/backend/scripts/linux/clean-dev-env.sh
```

The script builds the development images, starts services, runs migrations, and
loads test data. Backend source is mounted into the running containers so code
changes are picked up without rebuilding.

Local development services:

| Service | URL or port |
| --- | --- |
| Nginx entrypoint | `http://127.0.0.1:8000` |
| Django dev server | `http://127.0.0.1:9080` |
| Django admin | `http://127.0.0.1:8000/admin/` |
| PostgreSQL | `5432`, configurable by env file |
| Redis | `6379` |
| Celery Flower | `http://localhost:5555` |

Persistent development data is stored under `apps/backend/work/`. Running
`clean-dev-env.sh -d` wipes it.

## Compose Helpers

The helper scripts wrap the long Docker Compose command with the development env
files:

```sh
./apps/backend/scripts/linux/dc-dev.sh ps
./apps/backend/scripts/linux/dev-logs.sh
./apps/backend/scripts/linux/dev-manage.sh migrate
./apps/backend/scripts/linux/dev-manage.sh createsuperuser
```

Run helper scripts from the repository root unless a script documents otherwise.

## Django Commands

Use `dev-manage.sh` for commands inside the dev stack:

```sh
./apps/backend/scripts/linux/dev-manage.sh migrate
./apps/backend/scripts/linux/dev-manage.sh createsuperuser
./apps/backend/scripts/linux/dev-manage.sh flush
./apps/backend/scripts/linux/dev-manage.sh flush_sonarDB
```

SARS-CoV-2 sublineage search uses lineage parent-child data:

```sh
./apps/backend/scripts/linux/dev-manage.sh import_lineage
```

or with a specific file:

```sh
./apps/backend/scripts/linux/dev-manage.sh import_lineage \
  --lineages test-data/sars-cov-2/lineages_full_2025_09.tsv.xz
```

## Configuration

Development Docker env files live under `apps/backend/conf/docker/`.
PostgreSQL configs live under `apps/backend/conf/postgresql/`.

Local-only PostgreSQL overrides can be placed in ignored files such as
`dev.conf.local` or `prod.conf.local`.

## Tests

Backend tests use the backend test data and database setup.

```sh
cd apps/backend
poetry run pytest --cov -x tests/
```

If a test requires the Docker stack, start the relevant compose setup first.

## API Development Notes

The Django REST Framework browsable API is available in development mode at:

```text
http://127.0.0.1:8000/api/
```

The backend import path is asynchronous. When changing import behavior, verify
both the upload endpoint behavior and the worker-side database import behavior.

## Formatting

Repo-wide pre-commit hooks run Black, import sorting, YAML formatting, and
general whitespace checks. See the root
[CONTRIBUTING.md](../../CONTRIBUTING.md).
