# Frontend Contributing

This file covers source-based frontend development. Users should run the
frontend through the Docker deployment documented in [README.md](./README.md).

## Requirements

- Node.js
- npm
- A running Sonar backend

## Setup

From `apps/frontend`:

```sh
npm install
```

For local development, create a local backend URL override:

```sh
cp .env.development.local.example .env.development.local
```

The recommended backend URL for direct frontend development is:

```sh
VITE_SONAR_BACKEND_ADDRESS="http://localhost:9080/api/"
```

## Development Server

```sh
npm run dev
```

Common local URLs:

| Service | URL |
| --- | --- |
| Vite frontend | `http://localhost:5173` |
| Backend direct dev server | `http://localhost:9080/api/` |
| Backend through nginx | `http://localhost:8000/api/` |

Use the Vite frontend when working on UI code. Use the Docker-served frontend
when validating the deployment stack.

## Checks

```sh
npm run type-check
npm run lint
npm run format-check
npm run build
```

`npm run build:backend-proxy` builds the frontend and copies it into the backend
development work directory for nginx-served local testing.

## Production Build From Source

Source builds are mainly for contributors. Docker deployments should use the
published frontend image.

If you need a local static build:

```sh
VITE_SONAR_BACKEND_ADDRESS=https://example.org/api/ npm run build
```

Output is written to `dist/`.
