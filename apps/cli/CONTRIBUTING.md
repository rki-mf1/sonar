# CLI Contributing

This file covers source-based `sonar-cli` development. Users should prefer the
published Docker image documented in [README.md](./README.md).

## Requirements

- Conda or Mamba
- Poetry
- A running Sonar backend for integration workflows

## Environment

From `apps/cli`:

```sh
conda env update -n sonar -f environment.yml --prune
conda activate sonar
poetry install
```

The environment sets defaults used by common CLI workflows, including Java
options for SnpEff annotation.

Verify the CLI:

```sh
sonar-cli -v
sonar-cli info version
```

## Local Configuration

Copy the reference config if you want user-level defaults:

```sh
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/sonar-cli"
cp sonar-cli.config "${XDG_CONFIG_HOME:-$HOME/.config}/sonar-cli/sonar-cli.config"
```

Configuration precedence is command-line option, environment variable, user
config file, then built-in default.

## Tests

```sh
cd apps/cli
poetry run pytest --cov -n 2 --cache-clear --dist loadgroup -rfeP -x tests/
```

Use the backend development stack for tests or manual checks that need a live
API.

## Cache Internals

`sample import --cache` stores intermediate files so imports can resume and
failed samples can be inspected.

Typical cache layout:

```text
cache/
|-- anno/     # annotated variant files
|-- error/    # failed sample debug files
|-- ref/      # reference-derived files
|-- samples/  # per-sample metadata dictionaries
|-- seq/      # original sequences
`-- var/      # called variant files
```

Use `--debug` when you need to keep additional intermediate files for diagnosis.

## Alignment and Annotation

The CLI supports MAFFT, Parasail, and WFA2-based alignment. SnpEff is used for
variant annotation when `--auto-anno` is enabled.

If SnpEff runs out of memory:

```sh
export _JAVA_OPTIONS="-Xms512m -Xmx8g"
```

## Formatting

CLI linting is configured through `apps/cli/.flake8` and the root pre-commit
configuration. Run:

```sh
pre-commit run --all-files
```
