# Sonar Frontend

The Sonar frontend is the web interface for exploring data stored in Sonar. It
is aimed at users who want to browse samples, filter by metadata or mutations,
export results, and create charts without writing CLI commands.

For source development, see [CONTRIBUTING.md](./CONTRIBUTING.md).

## Run With Docker

The frontend is included in the Docker deployment bundle published on
[GitHub Releases](https://github.com/rki-mf1/sonar/releases):

```sh
curl -LO https://github.com/rki-mf1/sonar/releases/latest/download/sonar-docker-deploy-bundle.tar.gz
tar -xzf sonar-docker-deploy-bundle.tar.gz
cd example-deploy
./bootstrap.sh --tag latest
```

Default URL:

```text
http://localhost:18080
```

The prebuilt Docker image reads runtime settings when the container starts:

| Setting | Purpose |
| --- | --- |
| `SONAR_FRONTEND_BACKEND_ADDRESS` | Backend API URL used by the browser app. |
| `SONAR_FRONTEND_AUTH_TOKEN` | Optional token to inject when explicitly needed. |

In the deployment bundle, these settings live in `frontend.env`.

## What Users Can Do

The frontend provides three main areas:

| Area | Purpose |
| --- | --- |
| Home | Select organism, reference genome, and dataset. |
| Table | Browse, filter, inspect, and export samples. |
| Graph | Visualize filtered data with default and custom charts. |

The frontend is populated from the backend. If dropdowns are empty, first check
that the backend is running and that references and samples have been imported.

## Home Page

The Home page selects the working dataset:

- organism
- reference accession
- one or more datasets

After selection, the Table page opens with the matching samples.

## Table Page

The Table page is the primary browsing and filtering interface. Users can:

- sort and page through samples
- export the current result set
- open a sample detail panel
- inspect metadata and mutation profiles
- filter by collection date, lineage, DNA profile, or amino acid profile

Advanced filters support custom metadata fields and boolean grouping so users
can combine include and exclude conditions.

## Graph Page

The Graph page visualizes the currently filtered dataset. Default charts include
sample counts over time and lineage distributions over time. Users can also
create custom charts from available database fields.

Filters from the Table page continue to apply, so charts and tables describe the
same selected subset of samples.

## Connecting to the Backend

For Docker deployments, set `SONAR_FRONTEND_BACKEND_ADDRESS` in the extracted
bundle's `frontend.env`. Example:

```sh
SONAR_FRONTEND_BACKEND_ADDRESS=http://localhost:18000/api/
```

For source development with the Vite dev server, use
`.env.development.local` as described in [CONTRIBUTING.md](./CONTRIBUTING.md).
