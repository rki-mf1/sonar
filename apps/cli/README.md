# Sonar CLI

`sonar-cli` is the command-line tool for operating Sonar. It adds reference
genomes, imports sequences and metadata, runs preprocessing, checks import jobs,
and queries stored samples.

Use the CLI when you need to:

- register GenBank reference genomes
- import FASTA sequences with TSV or CSV metadata
- import public example datasets
- query samples by mutation profile, lineage, collection date, or custom metadata
- automate Sonar workflows from scripts or batch jobs

For local source development, see [CONTRIBUTING.md](./CONTRIBUTING.md).

## Recommended Usage: Docker

For users, the recommended path is the published Docker image:

```sh
docker run --rm \
  --env API_URL=http://127.0.0.1:18000/api \
  ghcr.io/rki-mf1/sonar-cli:latest reference list
```

If you are using the root [example deployment](../../example-deploy), prefer its
helper script:

```sh
cd ../../example-deploy
./sonar-cli.sh reference list
```

The helper mounts `example-deploy/data/`, reads `sonar-cli.config`, and points
the CLI at the deployment bundle backend API by default.

## Configuration

The CLI needs the backend API URL. Configuration precedence is:

1. command-line options such as `--db`
2. environment variables such as `API_URL`
3. `$XDG_CONFIG_HOME/sonar-cli/sonar-cli.config`
4. built-in defaults mirrored in `sonar-cli.config`

For the Docker deployment bundle, the default backend URL is:

```text
http://127.0.0.1:18000/api
```

For the backend development stack, common local URLs are:

```text
http://127.0.0.1:8000/api   # nginx entrypoint
http://127.0.0.1:9080/api   # direct Django dev server
```

To persist CLI settings:

```sh
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/sonar-cli"
cp sonar-cli.config "${XDG_CONFIG_HOME:-$HOME/.config}/sonar-cli/sonar-cli.config"
```

Edit the copied file and uncomment only the settings you want to override.

## Command Structure

```sh
sonar-cli <subject> <verb> [options]
```

Top-level subjects:

| Subject | Purpose |
| --- | --- |
| `reference` | Add, list, and delete reference genomes. |
| `property` | Add, list, and delete queryable metadata fields. |
| `sample` | Import, match, and delete samples. |
| `sequence` | Delete sequence data while preserving sample records. |
| `dataset` | Download and import supported public datasets. |
| `lineage` | Import lineage parent-child relationships. |
| `task` | List, inspect, and watch backend import jobs. |
| `info` | Show database information and statistics. |

Use help for exact options:

```sh
sonar-cli -h
sonar-cli sample import -h
```

## Add a Reference Genome

Reference genomes must be registered before importing samples.

```sh
./sonar-cli.sh reference add --genbank /data/sars-cov-2/MN908947.nextclade.gb
./sonar-cli.sh reference list
```

For multi-segment references, pass all GenBank files in one command:

```sh
sonar-cli reference add --genbank \
  CY115152.1.gbk \
  CY115153.1.gbk \
  CY115154.1.gbk \
  CY115155.1.gbk \
  CY115156.1.gbk \
  CY115157.1.gbk \
  CY115158.1.gbk \
  CY115159.1.gbk
```

Deleting a reference also removes samples and alignments associated with that
reference:

```sh
sonar-cli reference delete -r MN908947.3 --force
```

## Import Samples

`sample import` preprocesses sequences, calls mutations, optionally annotates
variants, and uploads the results to the backend for storage.

```sh
./sonar-cli.sh sample import \
  -r MN908947.3 \
  --fasta /data/sars-cov-2/SARS-CoV-2_12.fasta.xz \
  --tsv /data/sars-cov-2/SARS-CoV-2_12.tsv.xz \
  --cols \
    name=name \
    lineage=lineage \
    collection_date=collection_date \
  --auto-anno
```

Important options:

| Option | Purpose |
| --- | --- |
| `-r, --reference` | Reference accession to import against. |
| `--fasta` | FASTA input file or files. |
| `--tsv`, `--csv` | Metadata files. |
| `--cols PROP=COL` | Map database properties to metadata columns. |
| `--auto-link` | Link matching metadata columns automatically. |
| `--auto-anno` | Run SnpEff annotation during import. |
| `--cache DIR` | Keep intermediate files and resume interrupted imports. |
| `--method mafft|parasail|wfa` | Choose the alignment method. |
| `-t, --threads INT` | Number of worker threads. |

The `name` property must map to a unique sample identifier. It is used to detect
existing samples and to link metadata.

## Track Import Jobs

Imports are processed asynchronously by the backend.

```sh
sonar-cli task list
sonar-cli task show --jobid cli_...
sonar-cli task watch --jobid cli_... --interval 5
```

## Query Samples

Count samples for a reference:

```sh
sonar-cli sample match -r MN908947.3 --count
```

Match mutation profiles:

```sh
sonar-cli sample match -r MN908947.3 --profile C26270T
sonar-cli sample match -r MN908947.3 --profile S:E484K S:N501Y
sonar-cli sample match -r MN908947.3 --profile S:E484K --profile S:N501Y
```

Filter by metadata properties:

```sh
sonar-cli sample match -r MN908947.3 --lineage BA.2 --with-sublineage
sonar-cli sample match -r MN908947.3 --collection_date 2022-01-01:2022-12-31
```

Export results:

```sh
sonar-cli sample match -r MN908947.3 --format csv -o samples.csv
```

Use `sonar-cli property list` to inspect available metadata fields.

## Import Public Datasets

`dataset import` can download and import supported public datasets.

```sh
sonar-cli dataset import \
  --source pathoplexus \
  --pathogen mpox \
  -r NC_063383.1 \
  --sample-size 20 \
  --cache ./mpox_cache \
  --auto-link \
  --auto-anno
```

Supported sources include RKI and Pathoplexus. Use
`sonar-cli dataset import -h` to see the current source and pathogen choices.

## Troubleshooting

If SnpEff runs out of memory during annotation, increase the Java heap:

```sh
export _JAVA_OPTIONS="-Xms512m -Xmx8g"
```

If Docker cannot reach a local backend at `127.0.0.1`, use the
`example-deploy/sonar-cli.sh` helper on Linux or point `API_URL` to a hostname
reachable from the CLI container.
