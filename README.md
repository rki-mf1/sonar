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

# Installation

## 1. Prerequisite software

### 1.1 Install sonar-backend
please visit [sonar-backend](https://github.com/rki-mf1/sonar-backend)

## 2. Sonar-cli Setup

### 2.1 Download sonar-cli

```
https://github.com/rki-mf1/sonar-cli.git
cd sonar-cli
```

**Configuration**:

There is a ".env.template" file in the root directory. This file contains variables that must be used in the program and may differ depending on the environment. Hence, The ".env.template" file should be copied and changed to ".env", and then the variables should be edited according to your system.

### 2.2 Create python environment

```
conda create -n sonar-cli python=3.11 poetry snpeff snpsift
conda activate sonar-cli
```

### 2.3 SnpEff: configuration and custom database

1. Configure SnpEff: there is a default configuration file that comes with snpEff that we will customize. First, make a copy of that example config file in the sonar-cli directory. Make sure you are in the sonar-cli directory, and that the sonar-cli conda environment is active, then run:

```sh
cp $CONDA_PREFIX/share/snpeff-5.2.0/snpEff.config .
```

Open the `snpEff.config` file, which will contain various configuration options. Look for the `data.dir` parameter and specify the path where you want to store the SnpEff databases. For example, if you want to store the databases under the `/mnt/data` directory,

```sh
# snpEff.config setting, example
data.dir = /mnt/data/
```

You need to make sure this directory exists, as snpEff will not create it for you.

2. Then we need to obtain the database for annotation. We will use `buildDbNcbi.sh` script, which is also inside our sonar-cli conda environment. Unfortunately, the snpEff command used in the script is not correct for the version of snpEff installed via conda, so we need to fix that first:

```sh
$ cp "$CONDA_PREFIX/share/snpeff-5.2.0/scripts/buildDbNcbi.sh" .
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

Refer to the [SnpEff documentation](https://pcingola.github.io/SnpEff/) for more details.

### 2.4 Install application

```sh
poetry install --only main

# Test
sonar-cli -v
```

# Usage

The table below shows the several commands that can be used.

| subcommand | purpose                                                             |
|------------|---------------------------------------------------------------------|
| [import](#importing-genomes)   | import genome sequences and sample information to the database     |


## Importing Genomes

To see all available options
```
sonar-cli import -h
```

Example command:

```
sonar-cli import -r MN908947.3 --fasta covid19.fasta --cache cache_folder/ -t 2 --method 1 --auto-anno
```

Use Parasail as the alignment tool (`method 2`)
```
sonar-cli import -r MN908947.3 --fasta covid19.fasta --cache cache_folder/ -t 2 --method 2 --auto-anno
```

Include property during import
```
sonar-cli import -r MN908947.3 --fasta covid19.fasta --tsv covid19.meta.tsv --cache cache_folder/ -t 2 --method 1 --auto-anno --auto-link
```


# Contributing

Contributions to sonar-cli are welcome! If you encounter issues or have suggestions for improvements, please open an issue on the GitHub repository.

# License

This project is licensed under....

# Acknowledgments

This tool is built upon the foundations of covsonar and pathosonar projects.

Special thanks to the sonar contributors
