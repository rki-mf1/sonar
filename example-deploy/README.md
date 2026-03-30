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
   - frontend: `http://localhost:8080`
   - backend API: `http://localhost:8000/api/`

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

## CLI Usage

The matching CLI image is `${SONAR_CLI_IMAGE}` from `.env`. Example:

```sh
docker run --rm \
  --network example-deploy_default \
  --env API_URL=http://sonar-django-backend:9080/api \
  ${SONAR_CLI_IMAGE} list-ref
```

If you rename the compose project, adjust the network name accordingly.
