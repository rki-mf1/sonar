# Contributing

This file is for contributors working from source. User setup should stay in the
READMEs and should prefer the prebuilt Docker deployment path.

## Documentation Ownership

- Root `README.md`: short product overview, user value, Docker quick start, and links.
- `example-deploy/README.md`: detailed Docker deployment and operations guide.
- Component READMEs: user/operator documentation for that component.
- Root `CONTRIBUTING.md`: repo-wide contributor workflow, releases, and documentation rules.
- Component CONTRIBUTING files: source setup, tests, tooling, and internals for each component.

Keep phased-out source installation instructions out of user-facing READMEs.
Source-based setup belongs here or in a component-specific CONTRIBUTING file.

Component contributor docs:

- [Backend contributing](./apps/backend/CONTRIBUTING.md)
- [CLI contributing](./apps/cli/CONTRIBUTING.md)
- [Frontend contributing](./apps/frontend/CONTRIBUTING.md)

## Repository Layout

```text
apps/
|-- backend/    # backend API, database models, workers, deployment compose files
|-- cli/        # sonar-cli command line application
`-- frontend/   # web frontend
example-deploy/ # Docker Compose deployment from prebuilt images
test-data/      # small datasets and reference files used by examples and tests
```

## Pre-commit Hooks

Sonar uses pre-commit to catch formatting and lint issues before commit.

```sh
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Configured hooks include YAML checks, file ending checks, trailing whitespace
checks, Python import sorting, Black, YAML formatting, and CLI flake8 checks.

## Tests and Checks

Run checks in the component you changed:

- Backend: see [apps/backend/CONTRIBUTING.md](./apps/backend/CONTRIBUTING.md)
- CLI: see [apps/cli/CONTRIBUTING.md](./apps/cli/CONTRIBUTING.md)
- Frontend: see [apps/frontend/CONTRIBUTING.md](./apps/frontend/CONTRIBUTING.md)

For documentation-only changes, at minimum verify relative links and run
pre-commit if markdown files were edited.

## Versioning and Releases

Sonar uses one product version across the CLI, backend, and frontend.

For normal source changes, update the root `VERSION` file when the product
version should change. Local builds read this file when no build-time version is
provided.

After changing `VERSION`, synchronize component package metadata:

```sh
python scripts/sync-version.py
```

For releases, use a pull request for the version bump. Do not push directly to
`main`.

1. Create a release branch from the latest `main`.
2. Update `VERSION` to the release version, for example `1.2.3`.
3. Run `python scripts/sync-version.py`.
4. Open a pull request for the version bump and wait for the required checks.
5. Merge the pull request into `main`.
6. Update your local `main` to the merged commit:

   ```sh
   git switch main
   git pull --ff-only origin main
   ```

7. Create a Git tag on the merged `main` commit with the same version and a
   leading `v`, for example:

   ```sh
   git tag v1.2.3
   ```

8. Push the tag:

   ```sh
   git push origin v1.2.3
   ```

Release Docker images are stamped from the Git tag. The release workflow checks
that tag `vX.Y.Z` matches the root `VERSION` value `X.Y.Z`, and release
workflows reject tags that do not point to a commit already merged into `main`.
Keep the tag, `VERSION`, and merged `main` commit in sync.

## Documentation Review Checklist

Before merging documentation changes:

- If the frontend was updated, make sure the screenshot used for the README is kept up to date.
- User-facing setup uses prebuilt Docker images unless explicitly discussing contribution.
- Source-based setup is in CONTRIBUTING, not in README.
- Root README remains short enough to scan.
- Component READMEs link to detailed contributor docs instead of duplicating them.
- Commands match the current file layout and service names.
- Relative links resolve from the file where they appear.
