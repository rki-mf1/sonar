# sonar-cli

Sonar command line tool to interface with the [sonar-backend](https://github.com/rki-mf1/sonar/apps/backend) (API version; DjangoREST+PostgreSQL). Allows you to import new sequences and metadata.

[![Test&Check](https://github.com/rki-mf1/sonar-cli/actions/workflows/dev.workflow.yml/badge.svg?branch=dev)](https://github.com/rki-mf1/sonar-cli/actions/workflows/dev.workflow.yml)

![Static Badge](https://img.shields.io/badge/Maintenance%20status-actively%20developed-brightgreen)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

## Features

1. Import genomes: mutation calling and mutation import to database
2. query database with mutations profiles: Match profile
2. Support multiple genome references.
3. Support multiple alignment tools.
4. Cluster machine compatibility.

### For more information?, Visit 📚 [Sonar-CLI - Wiki Page](https://github.com/rki-mf1/sonar/apps/cli/wiki/) 🏃‍♂️

# QuickStart 🧬

## 1. Prerequisite software

### 1.1 Conda (Package manager)

- please visit [Miniconda](https://docs.anaconda.com/free/miniconda/) for download and installation
- please visit [Bioconda](https://bioconda.github.io/) for download and installation

### 1.2 Install sonar-backend

please visit [sonar-backend](https://github.com/rki-mf1/apps/backend) for download and installation

## 2. Sonar-cli Setup

### 2.1 Download sonar-cli

```sh
git clone https://github.com/rki-mf1/sonar.git
cd sonar/apps/cli
```

### 2.2 Configuration

🤓 There is a "env.template" file in the apps/cli directory. This file contains variables that must be used in the program and may differ depending on the environment. Hence, The ".env.template" file should be copied and changed to ".env", and then the variables should be edited according to your system.

```sh
cp env.template .env
```

### 2.3 Create python environment

```sh
conda env update -p ./env -f environment.yml --prune
conda activate ./env
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

It is also possible to build and run the sonar-cli using docker, but we still
have to figure out how to run commands like `import` which require access to
the filesystem outside of the container.

For now, you can build the cli container:

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

### Test Datasets

We provide the test datasets under the `test-data` directory.
| File              | Usage                                                                            |
| ----------------- | -------------------------------------------------------------------------------- |
| `sars-cov-2/180.sars-cov-2.zip` | Input sample containing the genomic sequence (fasta) and meta information (tsv). |
| `sars-cov-2/MN908947.nextclade.gb`  | Reference genome of SARS-CoV-2 in GenBank format.                                |

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

## Adding Reference

The `add-ref` subcommand is used to add reference genome sequences to the database.

```sh
sonar-cli add-ref --gb test-data/sars-cov-2/MN908947.nextclade.gb
```

## Importing Genomes

The `import` subcommand is used to import genome sequences and sample information into the database.

Basic command:

```sh
sonar-cli import -r MN908947.3 --fasta sars-cov-2.fasta --cache cache_folder/ -t 2 --method 1
```

Example command: Including properties during import

```sh
sonar-cli import -r MN908947.3 --fasta sars-cov-2.fasta --tsv sars-cov-2/meta.tsv --cache cache_folder/ -t 2 --method 1  --cols name=ID sequencing_tech=SEQUENCING_METHOD zip_code=DL.POSTAL_CODE  collection_date=DATE_OF_SAMPLING lab=SL.ID sample_type=SEQUENCE.SAMPLE_TYPE sequencing_reason=SEQUENCE.SEQUENCING_REASON  lineage=LINEAGE_LATEST
```

Example command: Including annotation step(`--auto-anno`)

```sh
sonar-cli import -r MN908947.3 --fasta sars-cov-2.fasta --tsv sars-cov-2/meta.tsv --cache cache_folder/ -t 2 --method 1  --cols name=ID  --auto-anno --auto-link
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

# 📄 License

This project is licensed under BSD.

# Acknowledgments

This tool is built upon the foundations of covsonar and pathosonar projects.

Special thanks to the sonar contributors
