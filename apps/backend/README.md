# Sonar Backend

The Sonar backend stores references, samples, metadata, mutations, annotations,
and import jobs. It provides the HTTP API used by the CLI and frontend.

For most users, the backend should be run through the Docker deployment bundle
published on [GitHub Releases](https://github.com/rki-mf1/sonar/releases).
Source-based backend setup is for contributors and is documented in
[CONTRIBUTING.md](./CONTRIBUTING.md).

## Role in Sonar

The backend is responsible for:

- registering GenBank reference genomes
- storing sample metadata and sequence-derived mutation profiles
- processing uploaded CLI import bundles asynchronously
- serving query, statistics, plot, and export data to the CLI and frontend
- exposing administrative operations through the API and Django admin

Typical import flow:

```text
sonar-cli uploads processed files
        |
        v
backend records an import job
        |
        v
worker processes files into the database
        |
        v
CLI, frontend, and API clients query stored data
```

## Run With Docker

Download and extract the latest deployment bundle:

```sh
curl -LO https://github.com/rki-mf1/sonar/releases/latest/download/sonar-docker-deploy-bundle.tar.gz
tar -xzf sonar-docker-deploy-bundle.tar.gz
cd example-deploy
./bootstrap.sh --tag latest
```

Default service URLs:

| Service | URL |
| --- | --- |
| Backend API | `http://localhost:18000/api/` |
| Django admin | `http://localhost:18000/admin/` |

For detailed configuration, see the `README.md` included in the extracted
deployment bundle.

## Configuration

The deployment bundle separates backend configuration into:

| File | Purpose |
| --- | --- |
| `.env` | Docker image tags and published host ports. |
| `backend.env` | Non-secret backend settings. |
| `backend.secrets.env` | Secret values such as database password and Django `SECRET_KEY`. |

Important settings include:

| Setting | Purpose |
| --- | --- |
| `ALLOWED_HOSTS` | Hostnames accepted by the backend. |
| `CORS_ALLOWED_ORIGINS` | Frontend origins allowed to call the API. |
| `SAMPLE_BATCH_SIZE` | Number of samples processed per backend worker batch. |
| `PROPERTY_BATCH_SIZE` | Number of metadata records processed per batch. |
| `CACHE_OBJECT_TTL` | Query cache lifetime in seconds. |
| `LOG_LEVEL` | Backend logging verbosity. |

For production, replace all generated secrets and use a fixed Docker image tag
instead of `latest`.

## API Overview

All API paths are relative to:

```text
http://<host>/api/
```

Common resource groups:

| Resource | Purpose |
| --- | --- |
| `/api/references/` | Reference genome records. |
| `/api/replicons/` | Genome segments or replicons. |
| `/api/genes/` | Gene annotation data. |
| `/api/samples/` | Sample records. |
| `/api/sample_genomes/` | Sequence data, mutation profile matching, and sample deletion. |
| `/api/properties/` | Custom metadata fields and values. |
| `/api/lineages/` | Lineage hierarchy and sublineage queries. |
| `/api/tasks/` | Import job status. |
| `/api/statistics/` | Database statistics. |
| `/api/plots/` | Plot data used by the frontend. |

The CLI is the recommended interface for imports. Direct API integration is
useful for custom dashboards, automation, or external services.

## Operations

Create a Django admin user in the Docker deployment:

```sh
cd example-deploy
docker compose exec sonar-backend python manage.py createsuperuser
```

Check backend readiness:

```sh
docker compose exec -T sonar-backend \
  curl --fail http://127.0.0.1:9080/api/database/get_database_tables_status/
```

View logs:

```sh
docker compose logs -f sonar-backend
```

## Performance Tuning

Throughput depends on CLI parallelism, backend worker settings, database tuning,
and input size.

Start with these deployment settings:

| Setting | Recommendation |
| --- | --- |
| CLI `-t / --threads` | Use available CPU cores for alignment and annotation. |
| `SAMPLE_BATCH_SIZE` | Increase carefully for throughput; reduce if workers use too much memory. |
| `PROPERTY_BATCH_SIZE` | Keep aligned with CLI metadata chunk size for large metadata imports. |
| `GUNI_WORKERS` | For production, size to available CPU and expected API traffic. |
| `LOG_LEVEL` | Use `INFO` or `WARNING` in production. |

For large deployments, tune PostgreSQL memory, worker concurrency, and Nginx
upload/timeouts together rather than changing one value in isolation.
