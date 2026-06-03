# Contributing

## Versioning and releases

Sonar uses one product version across the CLI, backend, and frontend.

For normal source changes, update the root `VERSION` file. Local builds read this
file when no build-time version is provided.

For releases:

1. Update `VERSION` to the release version, for example `1.2.3`.
2. Commit the version bump.
3. Create a Git tag with the same version and a leading `v`, for example:
   ```sh
   git tag v1.2.3
   ```
4. Push the tag:
   ```sh
   git push origin v1.2.3
   ```

Release container images are stamped from the Git tag. The release workflow
checks that tag `vX.Y.Z` matches the root `VERSION` value `X.Y.Z`, so keep them
in sync.
