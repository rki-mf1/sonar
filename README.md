# Sonar - Mutation Surveillance Platform

**Sonar** is a full-stack virus mutation surveillance tool consisting of:
- 🧬 A **command-line interface** for automated mutation calling and annotation based on genome sequences
- 🗃️ A **Django-based backend API** with PostgreSQL for storing and analyzing genomic data
- 🌐 A **Vue-based frontend** for interactive exploration of mutations and sample properties

| Component | Description                      | Path            | Documentation                                |
| --------- | -------------------------------- | --------------- | -------------------------------------------- |
| CLI       | Sequence import & processing tool    | `apps/cli`      | [CLI README](./apps/cli/README.md)       |
| Backend   | Django REST API & DB             | `apps/backend`  | [Backend README](./apps/backend/README.md)   |
| Frontend  | Web app for mutation exploration | `apps/frontend` | [Frontend README](./apps/frontend/README.md) |


---

## 🧭 System Architecture
apps/<br>
├── cli # Command line interface (Python + Poetry)<br>
├── backend # Django REST backend (PostgreSQL + Celery)<br>
└── frontend # Vue.js frontend (Vite + Vue 3 + Pinia)

A minimal setup requires a running CLI and backend. The frontend is optional and provides easier access to the data along with automated visualizations.

### 🧬 CLI (apps/cli)

The command line interface (CLI) is used to ingest sequences, metadata, and reference genomes. It provides easy commands for querying the backend.

    Supports multiple alignment tools (MAFFT, Parasail) and the mutation annotation tool SNPeff
    The import of Nextclade files is supported.

    Conda-based environment

See apps/cli/README.md for installation, usage examples, and test data.

### 🗃️ Backend (apps/backend)

A scalable backend built with Django REST + PostgreSQL to store genomic and metadata information, and serve it via APIs to the CLI and frontend.

    Dockerized and Celery-based for background processing

    Supports local development and production deployments

See apps/backend/README.md for setup instructions and deployment notes.

### 🌐 Frontend (apps/frontend)

An interactive web frontend built with Vue 3 and Vite, allowing users to:

    Explore genomic mutations and sample properties (e.g. lineages)

    Filter and visualize data interactively

See apps/frontend/README.md for setup and customization.

## Download sonar

```sh
git clone https://github.com/rki-mf1/sonar.git
cd sonar
```

## Deploy from prebuilt images

If you want to deploy sonar without cloning the repository, use the GHCR image
deployment bundle in [`example-deploy`](./example-deploy).

The release process also packages this directory as a downloadable
`sonar-ghcr-deploy-bundle.tar.gz` artifact. The bundle contains:

- an example `compose.yml`
- backend env and secrets templates
- frontend runtime config template

The published images are:

- `ghcr.io/rki-mf1/sonar-backend`
- `ghcr.io/rki-mf1/sonar-frontend`
- `ghcr.io/rki-mf1/sonar-cli`

## Local development

Local development remains source-based:

- backend development still uses the existing compose setup with source mounts
  and Django autoreload
- frontend development still uses the Vite dev server with automatic updates
  on file changes

The production image/deployment path is separate from the local contributor
workflow.
## Contributing

Contributions to sonar are welcome! If you encounter issues or have suggestions for improvements, please open an issue on the GitHub repository.

## 📄 License

This project is licensed under the GNU Affero General Public License (AGPL).
The third-party software libraries used are each licensed under their own licenses.
See LICENSE and THIRD-PARTY-LICENSES.txt for details.

## 🙏 Acknowledgments

This project has been developed as part of the following scientific initiatives:

- DAKI-FWS – Daten- und KI-gestütztes Frühwarnsystem zur Stabilisierung der deutschen Wirtschaft, funded by the Bundesministerium für Wirtschaft und Klimaschutz (BMWK).

- HERA – Health Emergency Preparedness and Response Authority, funded by the European Commission.

We also gratefully acknowledge the support of the Hasso Plattner Institute (HPI).

Sonar is built on the foundation of covsonar and mpoxsonar, with contributions from a wide range of collaborators.
Special thanks to all Sonar contributors for their invaluable input and dedication.
