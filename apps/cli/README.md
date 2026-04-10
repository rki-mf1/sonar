# sonar-cli

Sonar command line tool to interface with the [sonar-backend](https://github.com/rki-mf1/sonar/apps/backend) (API version; DjangoREST+PostgreSQL). Allows you to import new sequences and metadata.

[![Test&Check](https://github.com/rki-mf1/sonar-cli/actions/workflows/dev.workflow.yml/badge.svg?branch=dev)](https://github.com/rki-mf1/sonar-cli/actions/workflows/dev.workflow.yml)

![Static Badge](https://img.shields.io/badge/Maintenance%20status-actively%20developed-brightgreen)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

## Features

1. Import genomes: alignment against a reference genome of your choice, mutation calling and mutation import to database
2. Search: query database with mutation profiles or metadata (lineages, sampling dates, etc.)
2. Support multiple genome references.
3. Support multiple alignment tools.
4. Support for high performance compute clusters.

### For more information?, Visit 📚 [Sonar-CLI - Wiki Page](https://github.com/rki-mf1/sonar/apps/cli/wiki/) 🏃‍♂️

# QuickStart 🧬

## 1. Prerequisite software

### 1.1 Conda (Package manager)

We recommend [miniforge](https://conda-forge.org/download/), but other conda disributions will work as well.

### 1.2 Install sonar-backend

Please visit [sonar-backend](https://github.com/rki-mf1/apps/backend) for download and installation

## 2. Sonar-cli Setup

### 2.1 Download sonar-cli

```sh
git clone https://github.com/rki-mf1/sonar.git
cd sonar/apps/cli
```

### 2.2 Configuration

🤓 There is a `sonar-cli.config` file in the `apps/cli` directory. It is a
fully commented reference file that lists every configurable CLI setting and
its built-in default value. It can be copied to
`$XDG_CONFIG_HOME/sonar-cli/sonar-cli.config` (or `~/.config/sonar-cli/sonar-cli.config`)
if you want to persist those settings for your user account.

For contributor local development with `./apps/backend/scripts/linux/clean-dev-env.sh`,
the default backend URL is `http://127.0.0.1:9080/api`. In CI and in proxy-based
deployments, `http://127.0.0.1:8000/api` may still be used explicitly.

Configuration precedence for all settings is:

1. Explicit command-line option such as `--db`
2. Environment variable
3. `$XDG_CONFIG_HOME/sonar-cli/sonar-cli.config`
4. Built-in default values mirrored in `sonar-cli.config`

```sh
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/sonar-cli"
cp sonar-cli.config "${XDG_CONFIG_HOME:-$HOME/.config}/sonar-cli/sonar-cli.config"
```

Edit that copied file by uncommenting only the settings you want to override.

### 2.3 Create python environment

```sh
conda env update -n sonar -f environment.yml --prune
conda activate sonar
```

The same `conda env update` command can be used any time if you change your environment.yml file and want to update your environment to reflect the changes.

Environment variables:

The above environment file sets two environment variables to work around issues we've encountered so far. These are automatically set when you activate the environment:

1. SSL errors: `REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt`
2. [snpEff OutOfMemoryError](https://github.com/rki-mf1/sonar-cli/issues/72) (this bumps the memory up from 2GB to 4GB): `_JAVA_OPTIONS="-Xms128m -Xmx4g"`

### 2.4 Install sonar CLI

Navigate to the directory of `sonar/apps/cli`.

```sh
cd path/to/sonar/apps/cli
```

Install the application using Poetry.

```sh
poetry install --only main
```

Verify the installation by checking the version.

```sh
sonar-cli -v
```

Next make sure you can contact the backend:

```sh
$ sonar-cli list-ref
Current version sonar-cli:1.0.0
╒══════╤═════════════╤═══════════════╤═════════════════════════════════════════════════╕
│   id │ accession   │ taxon         │ organism                                        │
╞══════╪═════════════╪═══════════════╪═════════════════════════════════════════════════╡
│    1 │ MN908947.3  │ taxon:2697049 │ Severe acute respiratory syndrome coronavirus 2 │
╘══════╧═════════════╧═══════════════╧═════════════════════════════════════════════════╛
```

## 3. Sonar-cli Setup (Docker)

It is also possible to run the published sonar-cli image directly. For local
development, the conda + poetry workflow above remains the recommended path.

You can still build the cli container locally:

```
$ ./scripts/linux/build-docker.sh
```

Then you can run it, passing in whatever parameters you want:

```
$ ./scripts/linux/sonar-cli-docker.sh --help
usage: sonar-cli [-h] [-v]
                 {list-ref,add-prop,delete-prop,add-ref,delete-ref,import,delete-sample,list-prop,import-lineage,match,tasks}
                 ...

sonar-cli 1.0.0: Sonar command line tool to interface with the sonar-backend
and PostgreSQL version.

positional arguments:
  {list-ref,add-prop,delete-prop,add-ref,delete-ref,import,delete-sample,list-prop,import-lineage,match,tasks}
    list-ref            Lists all available references in the database
    add-prop            add a property to the database
[...]
```

The published image is `ghcr.io/rki-mf1/sonar-cli`. For example:

```sh
docker run --rm \
  --env API_URL=http://127.0.0.1:8000/api \
  ghcr.io/rki-mf1/sonar-cli:latest list-ref
```

Use `http://127.0.0.1:8000/api` when talking to the local development stack
through nginx. For the `example-deploy` bundle, use its published backend API
port instead, which defaults to `http://127.0.0.1:18000/api`.

For commands that read local files, mount the input directory into the
container:

```sh
docker run --rm \
  --env API_URL=http://127.0.0.1:8000/api \
  -v "$PWD/test-data:/data" \
  ghcr.io/rki-mf1/sonar-cli:latest import -r MN908947.3 --fasta /data/SARS-CoV-2_1000.fasta.xz
```

### Test Datasets

We provide the test datasets under the `test-data` directory.
| File              | Usage                                                                            |
| ----------------- | -------------------------------------------------------------------------------- |
| `test-data/sars-cov-2/180.sars-cov-2.zip` | Input sample containing the genomic sequence (fasta) and meta information (tsv). |
| `test-data/sars-cov-2/MN908947.nextclade.gb`  | Reference genome of SARS-CoV-2 in GenBank format.                                |

# Usage 🚀

The table below shows the several commands that can be used.

| Subcommand                        | Purpose                                                            |
| --------------------------------- | ------------------------------------------------------------------ |
| [import](#importing-genomes)      | Import genome sequences and sample information into the database.  |
| [match](#matching-genomes)        | Match genome sequences and sample information within the database. |
| [add-ref](#adding-reference)      | Add reference genome sequences to the database.                    |
| [delete-ref](#delete-reference)   | Delete reference genome sequences from the database.               |
| [list-ref](#listing-reference)    | List available reference genome sequences in the database.         |
| [list-prop](#listing-property)    | List queryable properties in the database.                         |
| [add-prop](#adding-property)      | Add property key for storage and querying in the database.         |
| [delete-prop](#deleting-property) | Delete properties in the database.                                 |
| [delete-sample](#deleting-sample) | Delete samples and associated information from the database.       |

> [!TIP]
> You can use `--db` to provide the URL to the backend (and it overwrites the configuration).
>
> for example, `sonar-cli add-ref --db "http://127.0.0.1:8000/api" --gb test-data/sars-cov-2/MN908947.nextclade.gb`
>
> for the `example-deploy` bundle, the corresponding default would be
> `sonar-cli add-ref --db "http://127.0.0.1:18000/api" --gb test-data/sars-cov-2/MN908947.nextclade.gb`

## Adding Reference

The `add-ref` subcommand is used to add reference genome sequences to the database.

```sh
sonar-cli add-ref --gb test-data/sars-cov-2/MN908947.nextclade.gb
```

## Importing Genomes

The `import` subcommand is used to import genome sequences and sample information into the database.

Basic command:

```sh
sonar-cli import -r MN908947.3 --fasta test-data/sars-cov-2/SARS-CoV-2_1000.fasta.xz --cache cache_folder/ -t 2 --method 1
```

Example command: Including properties during import

```sh
sonar-cli import -r MN908947.3 --fasta test-data/sars-cov-2/SARS-CoV-2_1000.fasta.xz --tsv test-data/sars-cov-2/SARS-CoV-2_1000.tsv.xz --cache cache_folder/ -t 2 --method 1  --cols name=ID sequencing_tech=SEQUENCING_METHOD zip_code=DL.POSTAL_CODE  collection_date=DATE_OF_SAMPLING lab=SL.ID sample_type=SEQUENCE.SAMPLE_TYPE sequencing_reason=SEQUENCE.SEQUENCING_REASON  lineage=LINEAGE_LATEST
```

Example command: Including annotation step(`--auto-anno`)

```sh
sonar-cli import -r MN908947.3 --fasta test-data/sars-cov-2/SARS-CoV-2_2.fasta.gz --tsv test-data/sars-cov-2/SARS-CoV-2_1000.tsv.xz --cache cache_folder/ -t 2 --method 1  --cols name=ID  --auto-anno --auto-link
```

To view all available options:

```sh
sonar-cli import -h
```

## Matching Genomes

The `match` subcommand is used to match genome sequences and sample information within the database.

List all mutations

```sh
sonar-cli match -r MN908947.3
```

With specific mutations (NT and AA) and count

```sh
sonar-cli match -r MN908947.3 --profile C26270T S:G339D --count
```

with mutations and property

```sh
sonar-cli match -r MN908947.3 --profile C26270T S:G339D --sequencing_tech ILLUMINA --format csv
```

## Deleting Reference

The `delete-ref` subcommand is used to delete reference genome sequences from the database.

```sh
sonar-cli delete-ref -r MN908947.3
```

## Listing Reference

The `list-ref` is used to list available reference genome sequences in the database.

```sh
sonar-cli list-ref
```

## Listing Property

The `list-prop` is used to list properties associated with genome sequences in the database.

```sh
sonar-cli list-prop
```

## Adding Property

The `add-prop` subcommand is used to add properties to genome sequences in the database.

```sh
sonar-cli add-prop --name test-prop --descr "hello world" --dtype value_varchar
```

## Deleting Property

The `delete-prop` subcommand is used to delete properties from genome sequences in the database.

```sh
sonar-cli delete-prop --name test-prop  --force
```

## Deleting Sample

The `delete-sample` is used to delete sample and associated information from the database.

User provides a sample ID using the `--sample` option or combine multiple IDs together with a file name using the `--sample-file` option (one ID per line in a file).

```sh
sonar-cli delete-sample --sample IMS-10116-CVDP-77AB96B7-B9FB-46D6-B844-F9356151F2CA --sample-file goodbye.txt
```

---

# Acknowledgments

This tool is built upon the foundations of covsonar and pathosonar projects.

Special thanks to the sonar contributors
