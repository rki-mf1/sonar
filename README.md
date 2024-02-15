# sonar-cli
Sonar command line tool to interface with the [sonar-backend](https://github.com/rki-mf1/sonar-backend) (API version; DjangoREST+PostgreSQL). Allows you to import new sequences and metadata.

![Static Badge](https://img.shields.io/badge/Lifecycle-Experimental-ff7f2a)

![Static Badge](https://img.shields.io/badge/Maintenance%20status-actively%20developed-brightgreen)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

## Features
1. Include standard features from covsonar and pathosonar (e.g., Import genome, Match profile)
2. Support multiple genome references.
3. Support multiple alignment tools.
4. Cluster machine compatibility.

# Installation 🧬

## 1. Prerequisite software

### 1.1 Conda (Package manager)

- please visit [Miniconda](https://docs.anaconda.com/free/miniconda/) for download and installation
- please visit [Bioconda](https://bioconda.github.io/) for download and installation

### 1.2 Install sonar-backend
please visit [sonar-backend](https://github.com/rki-mf1/sonar-backend) for download and installation

## 2. Sonar-cli Setup

### 2.1 Download sonar-cli

```sh
https://github.com/rki-mf1/sonar-cli.git
cd sonar-cli
```

### 2.2 Configuration

🤓 There is a "env.template" file in the root directory. This file contains variables that must be used in the program and may differ depending on the environment. Hence, The ".env.template" file should be copied and changed to ".env", and then the variables should be edited according to your system.

### 2.3 Create python environment

```sh
conda create -n sonar-cli python=3.11 poetry snpeff mafft
conda activate sonar-cli
```

### 2.4 SnpEff: configuration and custom database

#### 🤓By default, snpEff will download a SnpEff database if it is not available locally. The downloaded database will be stored under the same current activated python environment, for example, "/miniconda3/envs/sonar-cli/share/snpeff-5.2-0/data", so we can skip this section and ([go to next step 2.5-install-application](#25-install-application)) .

However, if we want to store the SnpEff database elsewhere, please follow the steps below.


1. Configure SnpEff: there is a default configuration file that comes with snpEff that we will customize. First, make a copy of that example config file in the sonar-cli directory. Make sure you are in the sonar-cli directory, and that the sonar-cli conda environment is active, then run:

```sh
cp $CONDA_PREFIX/share/snpeff-5.2-0/snpEff.config .
```

Open the `snpEff.config` file, which will contain various configuration options. Look for the `data.dir` parameter and specify the path where you want to store the SnpEff databases. For example, if you want to store the databases under the `/mnt/data` directory,

```sh
# snpEff.config setting, example
data.dir = /mnt/data/
```

You need to make sure this directory exists, as snpEff will not create it for you.

2. Then we need to obtain the database for annotation. We will use `buildDbNcbi.sh` script, which is also inside our sonar-cli conda environment. Unfortunately, the snpEff command used in the script is not correct for the version of snpEff installed via conda, so we need to fix that first:

```sh
$ cp $CONDA_PREFIX/share/snpeff-5.2-0/scripts/buildDbNcbi.sh .
$ sed -i -e 's/^java -jar snpEff.jar/snpEff/' buildDbNcbi.sh
$ tail -n 4 buildDbNcbi.sh

# Build database
snpEff build -v $ID

```

Be sure that line says "snpEff" and not something like "java -jar snpEff.jar ...".

Now we can actaully use the script to build a database. The command fetches the required data from the NCBI and generates the necessary database files for annotation.

```sh
# command
./buildDbNcbi.sh <genome accesion number>
# example
./buildDbNcbi.sh MN908947.3
```

3. After the buildDbNcbi command is done, Do not forget to copy folder name "<genome accession number>" under the "data/" folder to the designed path according to the "data.dir" variable (in snpEff.config)

In our case, for example:
```sh
mv data/MN908947.3 /mnt/data/
```

Refer to the [SnpEff documentation](https://pcingola.github.io/SnpEff/) for more details.

4. Edit ".env" file of sonar-cli, we have provide the full path of snpEff.config in the ANNO_CONFIG_FILE variable within the ".env" file.
```sh
# example
ANNO_CONFIG_FILE=/path/to/snpEff.config
```

### 2.5 Install application

Navigate to the root directory of `sonar-cli`.
```sh
cd path/to/sonar-cli
```

Install the application using Poetry.

```sh
poetry install --only main
```

Verify the installation by checking the version.
```sh
sonar-cli -v
```


### Test Datasets

We provide the test datasets under the `test-data` directory. These datasets can be used in `sonar-backend` commands and Insomnia API for testing.

| File                       | Usage                                        |
|----------------------------|----------------------------------------------|
| `180.covid19.zip`       | Input sample containing the genomic sequence (fasta) and meta information (tsv). |
| `MN908947.3.gbk`            | Reference genome of SARS-CoV-2 in GenBank format.                          |

# Usage 🚀


### Full Explanation 📚: [Sonar-CLI Commands - Wiki Page](https://github.com/rki-mf1/sonar-cli/wiki/Sonar%E2%80%90CLI-Commands)


The table below shows the several commands that can be used.

| Subcommand | Purpose                                                            |
|------------|--------------------------------------------------------------------|
| [import](#importing-genomes) | Import genome sequences and sample information into the database.   |
| [match](#matching-genomes) | Match genome sequences and sample information within the database.  |
| [add-ref](#adding-reference) | Add reference genome sequences to the database.                     |
| [delete-ref](#delete-reference) | Delete reference genome sequences from the database.              |
| [list-ref](#listing-reference) | List available reference genome sequences in the database.          |
| [list-prop](#listing-property) | List queryable properties in the database.   |
| [add-prop](#adding-property) | Add property key for storage and querying in the database.                 |
| [delete-prop](#deleting-property) | Delete properties in the database.          |
| [delete-sample](#deleting-sample) | Delete samples and associated information from the database. |

> [!TIP]
> You can use `--db` to provide the URL to the backend (and it overwrites the configuration).
>
> for example, `sonar-cli add-ref --db "http://127.0.0.1:8000/api" --gb MN908947.3.gbk`

## Adding Reference
The `add-ref` subcommand is used to add reference genome sequences to the database.
```sh
sonar-cli add-ref --gb MN908947.3.gbk
```

## Importing Genomes
The `import` subcommand is used to import genome sequences and sample information into the database.

Basic command:
```sh
sonar-cli import -r MN908947.3 --fasta covid19.fasta --cache cache_folder/ -t 2 --method 1
```

Example command: Including properties during import
```sh
sonar-cli import -r MN908947.3 --fasta covid19.fasta --tsv covid19.meta.tsv --cache cache_folder/ -t 2 --method 1  --cols sample=ID sequencing_tech=SEQUENCING_METHOD zip_code=DL.POSTAL_CODE  collection_date=DATE_OF_SAMPLING lab=SL.ID sample_type=SEQUENCE.SAMPLE_TYPE sequencing_reason=SEQUENCE.SEQUENCING_REASON  lineage=LINEAGE_LATEST
```

Example command: Including annotation step(`--auto-anno`)
```sh
sonar-cli import -r MN908947.3 --fasta covid19.fasta --tsv covid19.meta.tsv --cache cache_folder/ -t 2 --method 1  --cols sample=ID  --auto-ano --auto-link
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

----

# Contributing

Contributions to sonar-cli are welcome! If you encounter issues or have suggestions for improvements, please open an issue on the GitHub repository.

# License

This project is licensed under....

# Acknowledgments

This tool is built upon the foundations of covsonar and pathosonar projects.

Special thanks to the sonar contributors
