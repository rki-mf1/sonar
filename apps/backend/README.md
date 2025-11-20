# Sonar Backend

The sonar backend is web service provides the postgres database and Rest-API for scalability and integration with the web application.

![Static Badge](https://img.shields.io/badge/Maintenance%20status-actively%20developed-brightgreen)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![DjangoREST](https://img.shields.io/badge/DJANGO-REST-ff1709?style=for-the-badge&logo=django&logoColor=white&color=ff1709&labelColor=gray)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)

**Please visit [sonar-backend wiki](https://github.com/rki-mf1/sonar/apps/backend/wiki) for more details**

# Setup

## General organization

### Docker Configuration

We use docker compose to manage the software stack (the django backend itself, celery workers, the PostgreSQL database, ...). This is setup mainly in the `compose.yml` file in the project root. This compose file exposes the minimum ports, so for development there is an additional compose file `compose-dev.yml` that is loaded **in addition to** the main compose file, which just opens up a few more ports to a few of the services, and also mounts the source directory as a volume for all django containers to that you can do live editing of the code without having to rebuild your docker container:

```
$ docker compose -f compose.yml -f compose-dev.yml
```

To configure the containers, a set of config/environment files from the `conf/docker/` directory are loaded. For dev, that includes (in order) `common.env`, `dev.env`, and `dev-secret.yml`. For production, we load `common.env`, `prod.env` and `prod-secrets.env`. Each config file can overwrite settings in the previous, so you can overwrite "common" settings in the `dev.env` file and settings from both `common.env` and `dev.env` can be overwritten in the `dev-secrets.env` file.

The `prod-secrets.yml` file is **not** supposed to be checked into git, and should contain things like the Django `SECRET_KEY` as well as variaous default passwords for services like PostgreSQL. You can see the minimum varialbes that you should include in that file in the matching `dev-secrets.env` file, which gives examples for each of the secrets which should obviously not be reused in production.

Taking the previous points into account, the development environment using docker compose is interacted with like this:

```
$ docker compose -f compose.yml -f compose-dev.yml --env-file conf/docker/common.env --env-file conf/docker/dev.env --env-file conf/docker/dev-secrets.env <your command here>
```

That is a huge command, so we have convenience scripts here: `scripts/{linux,windows}/dc-{dev,prod}.{sh,ps1}` These helpers are used by all other convenience scripts so changes to this command line are easier to make, if we need to do that in the future.

Note: for now, we specifically don't use the `env_file:` directive in our compose files. This is because it further fragments where the configuration is stored and also seemed to lead to some duplication in the config files. The downside to this is that the `environment:` sections of the current compose file have lots of duplication and are very long, and this can eventually lead to bugs when someone forgets to add a new environment variable to all necessary containers. With that in mind we might revisit using env_files in the future if the benefits are deemed to outweight the costs.

### PostgreSQL Configuration

Postgres configuration files are in the `./conf/postgresql/` directory. The main config files you'll want to use are either `prod.conf` or `dev.conf`. You can choose which config file you use by setting the variable `POSTGRES_CONFIG_FILE` in the docker config file (see above):

```
POSTGRES_CONFIG_FILE=dev.conf
```

Both `dev.conf` and `prod.conf` are set up to include `common.conf`, then contain a few settings that are recommended for development or production use, and then additionally include a `dev.conf.local` or `prod.conf.local` file if it exists. This file is excluded from git and you can use it to include some local-only custom Postgres settings such as aggressive logging options or disabled fsync.

For reference, the config directory also includes `default-config-notused.conf` which lists most configuration settings and their defaults.

## Production

### Software requirements

We have currently tested running producion on a server with:

Operating system: Ubuntu 24.04
CPU cores: 4
RAM: 16 GB

We deploy using a non-root user, so the following software needs to be set up
by an administrator:
- rootless docker (set up to be used by your user)
- an SSL proxy forwarding port 443 to 8000

Your user can then setup the following:
- mamba

Now we need to clone the sonar-backend repo:

```bash
git clone https://github.com/rki-mf1/sonar.git
cd sonar/apps/backend
```

Next we need to set up secret information that will be unique to your installation. These values need to be defined in `backend/conf/docker/prod-secrets.env`. To see which values need to be set, you can check the `backend/conf/docker/dev-secrets.env` file but **do not just copy the values from this file**. You need to set your own passwords and Django SECRET_KEY.

To generate a new Django SECRET_KEY, you can run the following (needs Python >=3.6):

```bash
$ python -c "import secrets; print(secrets.token_urlsafe())"
<the secret key will be here>
```

Now you can add that value to your secrets file:

```bash
nano conf/docker/prod-secrets.env
```

Next we need to build the sonar-backend docker container, bring up all services and run Django migrations. We pass the `-t` argument because we do not want to include test data (you can remove this if you want to load some test data).

```bash
$ ./scripts/linux/clean-prod-env.sh -t
```



## Development

**⚠️Caution: The setting and installation steps can vary depending on the user; this was just an example guideline.**

The current version has been tested on the following system configurations:

- Ubuntu ^22.04
- docker
- mamba

  > [!note] > **🗿 Recommended software:** DB Management Software (e.g. DBeaver), REST Client (e.g. Insomnia, Insomnia configuration can be shared)

### Install sonar-backend

First, clone the project:

```bash
$ git clone https://github.com/rki-mf1/sonar.git
```

Next, you can start up a dev instance of the software stack using docker compose (use the `-h` argument to see other options for this script):

```bash
$ ./apps/backend/scripts/linux/clean-dev-env.sh
```

After that command finishes, you should have the following services running on these ports:

- 9080: django app server (`manage.py runserver`)
- 8000: nginx forwarding requests to the django dev appserver on port 9080. You can access the django admin interface at `localhost:8000/admin`
- 5432 (configurable by env file): PostgreSQL database
- 6379: redis used by celery
- 5555: celery monitor web interface

Files from the containers that need to persist across restarts (e.g. the postgres databases themselves, mutation and metadata from imports, etc.) are all stored in subdirectories of the `./work/` dir. This directory will be removed if you run `clean-dev-env.sh -d`.

### Sublineage Search (optional, SARS-CoV-2 specific)

To enable sublineage search for SARS-CoV-2, you must first import the Parent-Child relationship. Use the following command to download the latest version of lineages from [cov-lineages/pango-designation](https://github.com/cov-lineages/pango-designation/) and import it into the database automatically:

```bash
python apps/backend/manage.py import_lineage
```

If you have a specific file from pangoline that you manually downloaded, you can specify it using the following command:

```bash
python apps/backend/manage.py import_lineage --lineages test-data/lineages_2024_01_15.csv
```

### **Note:**

- `apps/backend/manage.py` is used for all django commands
- `python ./apps/backend/manage.py migrate` commits all migration db changes to the database. also creates django specific administrative tables
- `python ./apps/backend/manage.py createsuperuser` creates a user with full access to all db operations and to the admin page
- `python ./apps/backend/manage.py runapscheduler` starts the appscheduler, which then enables jobs (as of now used for imports, see below). can be canceled after running, as of now only used to setup the jobs for manual use.
- `python ./apps/backend/manage.py runserver` starts the development server. in 99% of cases no restart is needed to apply changes to the django code. While running, the terminal will output any api requests and `print` statements. exceptions will not be printed automatically.

### Misc

- Access dev. admin page should be reached under [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) for login see `createsuperuser` above
- To reset the entire database, use the command:
  ```bash
  python apps/backend/manage.py flush
  ```
  If you only want to reset the tables related to the Sonar database, use:
  ```bash
  python apps/backend/manage.py flush_sonarDB
  ```
- During development, we use [Insomnia](https://insomnia.rest/) for API testing. To facilitate testing, we provide the API collection in the file `apps/backend/resource/Insomnia_XXXX.json`. The datasets can be found under the `test-data` folder. You can easily import the collection into your Insomnia API client and start testing."

### Test Datasets

We provide the test datasets under the `test-data` directory. These datasets can be used in `sonar-backend` commands and Insomnia API for testing.

| File                     | Usage                                                                                                                 |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `test-data/sars-cov-2/lineages_full_2025_09.tsv`           | Used in the `python manage.py import_lineage` command.                              |
| `test-data/sars-cov-2/SARS-CoV-2_12.fasta.xz`        | 12 fasta sequences of SARS-CoV-2.                                                    |
| `test-data/sars-cov-2/SARS-CoV-2_12.tsv.xz`         |   Input sample containing meta information (tsv).                              |
| `test-data/sars-cov-2/MN908947.nextclade.gb`         | Reference genome of SARS-CoV-2 in GenBank format.                                         |
| `apps/backend/conf/initdb-test/dump-sonar-12-test-db.sql` | SQL dump files, an easy way to test by importing the SQL file into the database for testing and working with pytest." |

### Extra docker compose commands

1. Create superuser for Django admin

```bash
# docker-compose exec <service_name>, not docker-compose exec <container_name>.
./apps/backend/scripts/linux/dev-manage.sh createsuperuser
```

Once the containers are up and running, you can access

- sonar-cli reach the backend via http://127.0.0.1:8000/api
- http://127.0.0.1:8000/admin
- http://localhost:5555 for monitoring workers (username:"admin" password:"123456")

---

# API Queries Reference

## Base Information

**Base URL:** `/api/`

**Authentication:** Django REST Framework

**Response Format:** JSON

---

## 1. Samples (Genomic Samples)

### 1.1 List All Samples
```
GET /api/samples/
```

**Parameters:**
- `filters` (optional): JSON with filter conditions
- `reference_accession`: Reference accession of genome
- `ordering`: Ordering field (e.g., `-collection_date`)
- `name`: Filter by sample name

**Response:**
```json
{
  "count": 123,
  "next": "https://...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "SAMPLE-001",
      "sequences": [1, 2],
      "collection_date": "2024-01-15",
      "lineage": "BA.2.86",
      "init_upload_date": "2024-01-20",
      "last_update_date": "2024-01-22"
    }
  ]
}
```

### 1.2 Retrieve Single Sample
```
GET /api/samples/{name without slash}/
```

**Response:** Detailed sample object (see above)

### 1.3 Get Sample Statistics
```
GET /api/samples/statistics/
```

**Parameters:**
- `reference` (optional): Reference accession (/api/samples/statistics/?reference=MN908947.3)

**Response:**
```json
{
  "samples_total": 1500,
  "first_sample_date": "2023-01-10",
  "latest_sample_date": "2024-12-15",
  "populated_metadata_fields": ["country", "age", "lineage"]
}
```

### 1.4 Get Filtered Statistics
```
GET /api/samples/filtered_statistics/
GET /api/samples/filtered_statistics/?filters={"andFilter":[],"orFilter":[]}&reference_accession="NC_026438.1"
```

**Parameters:**
- `filters`: JSON with filter conditions
- `reference_accession`: Reference accession

**Response:**
```json
{
  "filtered_total_count": 342
}
```

### 1.5 Get Genomes (Genomic/Proteomic Profiles)
```
GET /api/samples/genomes/
GET /api/samples/genomes/?limit=10&offset=0&ordering=-collection_date&filters={"andFilter":[{"label":"DNA/AA '
 'Profile","value":"NC_026438.1:A1019G","exclude":false}], "orFilter":[]}&reference_accession="NC_026438.1"
```

**Parameters:**
- `filters`: JSON with filter conditions (required)
- `reference_accession`: Reference accession
- `name`: Filter by sample name
- `showNX` (boolean): Show ambiguous nucleotides (default: False)
- `csv_stream` (boolean): Return CSV stream
- `vcf_format` (boolean): Return VCF format
- `ordering`: Ordering field
- `columns`: For CSV export (comma-separated)
- `filename`: Filename for CSV download

**Example Filter:**
```json
{
  "reference_accession": "NC_026438.1",
  "andFilter": [{"label":"DNA/AA Profile","value":"NC_026438.1:A1019G","exclude":false}],
  "orFilter": []
}
```

**Response (Standard):**
```json
{
  "count": 50,
  "results": [
    {
      "id": 1,
      "name": "SAMPLE-001",
      "sequences": [1, 2, 3],
      "genomic_profiles": {
        "NC_026438.1": {
          "G161A": ["missense_variant MODERATE"],
          "C666T": ["synonymous_variant LOW"],
        },
        "NC_026437.1": {
          "C39T": ["synonymous_variant LOW"],
          "R53A": ["missense_variant MODERATE"],
        }
      },
      "proteomic_profiles": {
        "YP_009742039.1": ["S:D614G", "S:L452R"],
        "YP_009118630.1": ["PA:X18E","PA:A20T"],
      },
      "properties": [
        {"name": "country", "value": "Germany"},
        {"name": "age", "value": "45"},
        {"name": "init_upload_date", "value": "2025-11-14"},
        {"name": "last_update_date", "value": "2025-11-19"}
      ],
      "init_upload_date": "2025-11-14T13:55:28.948748Z",
      "last_update_date": "2025-11-19T11:02:31.412329Z"
    }
  ]
}
```

### 1.6 Export Genomes as CSV Stream
```
GET /api/samples/genomes/?csv_stream=true&columns=name,country,collection_date,genomic_profiles
```

**Response:** CSV file for download

### 1.7 Export Genomes in VCF Format
```
GET /api/samples/genomes/?vcf_format=true
```

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "name": "SAMPLE-001",
      "genomic_profiles": {
        "NC_045512.2": [
          {
            "variant.id": 123,
            "variant.ref": "A",
            "variant.alt": "G",
            "variant.start": 23402,
            "variant.end": 23403
          }
        ]
      }
    }
  ]
}
```

### 1.8 Get Distinct Lineages
```
GET /api/samples/distinct_lineages/
```

**Parameters:**
- `reference` (optional): Reference accession

**Response:**
All lineages of samples (selected organism = reference_accession)
```json
{
  "lineages": ["BA.2.86", "XEC", "JN.1", "XEC.1.1", null]
}
```

### 1.9 Get All Lineages
```
GET /api/samples/full_lineages/
```
**Parameters:**
- `reference` (optional): Reference accession

**Response:**
All lineages of the selected organism.
```json
{
  "lineages": ["A", "B", "BA", "BA.1", "BA.2", "BA.2.86", ...]
}
```

### 1.10 Get Metadata Coverage
```
GET /api/samples/plot_metadata_coverage/
```

**Parameters:**
- `filters`: JSON with filter conditions

**Response:**
```json
{
  "metadata_coverage": {
    "country": 1200,
    "age": 850,
    "collection_date": 1500,
    "sequencing_reason": 320,
    "lineage": 0,
  }
}
```

### 1.11 Samples Per Week (Chart Data)
```
GET /api/samples/plot_samples_per_week/
```

**Parameters:**
- `filters`: JSON with filter conditions

**Response:**
```json
[
  ["2024-W01", 45],
  ["2024-W02", 62],
  ["2024-W03", 58]
]
```

### 1.12 Lineages Per Week (Chart Data)
```
GET /api/samples/plot_grouped_lineages_per_week/
```

**Parameters:**
- `filters`: JSON with filter conditions

**Response:**
```json
{
  "grouped_lineages_per_week": [
    {
      "week": "2024-W01",
      "lineage_group": "BA.2",
      "count": 28,
      "percentage": 62.22
    },
    {
      "week": "2024-W01",
      "lineage_group": "XEC",
      "count": 17,
      "percentage": 37.78
    }
  ]
}
```

### 1.13 Get Custom Property Plot
```
GET /api/samples/plot_custom/?property={property_name}
```

**Parameters:**
- `filters`: JSON with filter conditions
- `property`: Property name (e.g., `sequencing_reason`)

**Response:**
```json
{
  "sequencing_reason": {
    "Surveillance": 850,
    "Clinical": 420,
    "Research": 230
  }
}
```

### 1.14 Get XY-Axis Plot (Two Properties)
```
GET /api/samples/plot_custom_xy/?x_property=country&y_property=sequencing_reason
```

**Parameters:**
- `filters`: JSON with filter conditions
- `x_property`: X-axis property name
- `y_property`: Y-axis property name

**Response:**
```json
{
  "Germany": [
    {"Surveillance": 420},
    {"Clinical": 180}
  ],
  "France": [
    {"Surveillance": 320},
    {"Clinical": 140}
  ]
}
```

### 1.15 Get Sequence Data
```
GET /api/samples/get_sequence_data/?sequence_name={sequence_name}
```

**Response:**
```json
{
  "sequence_id": 42,
  "name": "IMS-SEQ-01",
  "sequence_seqhash": "abc123def456"
}
```

### 1.16 Get Bulk Sequence Data
```
POST /api/samples/get_bulk_sequence_data/
```

**Request Body:**
```json
{
  "sequence_data": ["IMS-SEQ-01", "IMS-SEQ-04", "IMS-SEQ-07"]
}
```

**Response:**
```json
[
  {
    "sequence_id": 1,
    "name": "IMS-SEQ-01",
    "sequence_seqhash": "abc123"
  },
  {
    "sequence_id": 4,
    "name": "IMS-SEQ-04",
    "sequence_seqhash": "def456"
  },
  {
    "sequence_id": null,
    "name": "IMS-SEQ-07",
    "sequence_seqhash": null
  }
]
```

### 1.17 Delete Samples
```
POST /api/samples/delete_sample_data/
```

**Request Body:**
```json
{
  "reference_accession": "NC_045512.2",
  "sample_list": "[\"SAMPLE-001\", \"SAMPLE-002\"]"
}
```

**Response:**
```json
{
  "status": "success",
  "deleted_count": 2
}
```

### 1.18 Delete Sequences
```
POST /api/samples/delete_sequence_data/
```

**Request Body:**
```json
{
  "reference_accession": "NC_045512.2",
  "sequence_list": "[\"IMS-SEQ-01\", \"IMS-SEQ-02\"]"
}
```

**Response:**
```json
{
  "status": "success",
  "deleted_count": 2
}
```

---

## 2. Sample Genomes via CLI match

### 2.1 Match Sample Genomes
```
GET /api/sample_genomes/match/
```

**Parameters:**
- `profile_filters`: List of profile filters
- `param_filters`: List of parameter filters

**Response:** Filtered genomes

---

## 3. Database Information

### 3.1 Get Database Tables Status
```
GET /api/database/get_database_tables_status/
```

**Response (Success):**
```json
{
  "status": true
}
```

**Response (Missing Tables):**
```json
{
  "status": false,
  "missing_tables": ["sample", "sequence", "alignment"]
}
```

### 3.2 Get Database Info
```
GET /api/database/get_database_info/
```

**Response:**
```json
{
  "detail": {
    "metadata_coverage": {
            "id": "111 (100.00%)",
            "name": "111 (100.00%)",
            "lineage": "12 (10.81%)",
    },
    "samples_total": 1500,
    "earliest_sampling_date": "2023-01-10",
    "latest_sampling_date": "2024-12-15",
    "earliest_genome_import": "2023-01-15",
    "latest_genome_import": "2024-12-18",
    "unique_sequences": 8420,
    "genomes": 12500,
    "reference_genome":  "Severe acute respiratory syndrome coronavirus 2": {
                "replicons": ["MN908947.3 (Wuhan-Hu-1/2019)"],
                "reference_length": [29903],
                "annotated_proteins": "E, M, N, ORF1a, ORF1b, ORF3a, ... "
            },
            "Monkeypox virus": {
                "replicons": ["NC_063383.1 Monkeypox virus, complete genome"],
                "reference_length": [197209],
                "annotated_proteins": "OPG001, OPG002, ..."
            },
    "reference_length": 29903,
    "annotated_proteins": "E, M, N, ORF1a, ORF1ab, ORF3a, ORF6, ORF7a, ORF7b, ORF8, ORF10, S",
    "database_size": "2.5 GB",
    "database_version": "PostgreSQL 14.2 on x86_64-pc-linux-gnu"
  }
}
```

---

## 4. Additional Endpoints

### 4.1 References
```
GET /api/references/
```

### 4.2 Replicons
```
GET /api/replicons/
```

### 4.3 Alignments
```
GET /api/alignments/
```

### 4.4 Properties
```
GET /api/properties/
```

### 4.5 Genes
```
GET /api/genes/
```

### 4.6 Lineages
```
GET /api/lineages/
```

---

## 5. Filter Syntax

### Mutation Filters, Label "DNA/AA Profile"
NC_045512.2 = replicon accession

**SNP Nucleotide:** `A23403G` or `NC_045512.2:A23403G`

**SNP Protein:** `S:D614G` or `NC_045512.2:S:D614G`

**Deletion Nucleotide:** `del:21563-21575` or `NC_045512.2:del:21563-21575`

**Deletion Protein:** `S:del:140-145` or `NC_045512.2:S:del:140-145`

**Insertion Nucleotide:** `T133102TTT` or `NC_045512.2:T133102TTT`

**Insertion Protein:** `S:A34AK` or `NC_045512.2:S:A34AK`

### Complex Filters (JSON)

```json
{
  "reference_accession": "NC_1235512.2",
  "label": "SNP Nt",
  "value": "A23403G",
  "andFilter": [
    {
      "label": "Property",
      "property_name": "country",
      "filter_type": "exact",
      "value": "Germany"
    }
  ],
  "orFilter": [
    {
      "label": "SNP AA",
      "value": "S:D614G"
    }
  ]
}
```

### Filter Types

| Type | Description | Example |
|------|-------------|---------|
| `exact` | Exact match | `value: "Germany"` |
| `contains` | Contains substring | `value: "%Berlin%"` |
| `range` | Range query | `value: "10,50"` |
| `in` | In list | `value: ["A", "B"]` |
| `isnull` | Is null | `value: true` |

---

## 6. Pagination

All list endpoints support pagination:

```json
{
  "count": 1500,
  "next": "https://api.example.com/api/samples/?page=2",
  "previous": null,
  "results": [...]
}
```

**Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Entries per page (default: 20)

---

## 7. Usage Examples

### Example 1: Get all samples from Germany
```bash
curl "http://localhost:8000/api/samples/genomes/?reference_accession=NC_045512.2&filters=%7B%22label%22:%22Property%22,%22property_name%22:%22country%22,%22filter_type%22:%22exact%22,%22value%22:%22Germany%22%7D"
```

### Example 2: Find samples with specific mutation
```bash
curl "http://localhost:8000/api/samples/genomes/?reference_accession=NC_045512.2&filters=%7B%22label%22:%22SNP%20Nt%22,%22value%22:%22A23403G%22%7D"
```

### Example 3: Export samples as CSV
```bash
curl "http://localhost:8000/api/samples/genomes/?reference_accession=NC_045512.2&csv_stream=true&columns=name,country,collection_date&filters=%7B%7D" -o samples.csv
```

### Example 4: Get database status
```bash
curl "http://localhost:8000/api/database/get_database_tables_status/"
```

---

## 9. Rate Limiting and Performance

- Large result sets are automatically paginated
- Use `csv_stream=true` for efficient bulk exports
- Consider filtering early to reduce query complexity
- Use `showNX=false` to exclude ambiguous nucleotides for better performance

# Acknowledgments

This tool is built upon the foundations of covsonar and mpoxsonar projects.

Special thanks to all sonar contributors...
