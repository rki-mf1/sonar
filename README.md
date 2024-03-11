# sonar-backend

The sonar-backend is web service that represents the API version of the Sonar tool (covsonar), which utilizes Django REST + PostgreSQL for scalability and integration with the web application.

![Static Badge](https://img.shields.io/badge/Lifecycle-Experimental-ff7f2a)

![Static Badge](https://img.shields.io/badge/Maintenance%20status-actively%20developed-brightgreen)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) 
![DjangoREST](https://img.shields.io/badge/DJANGO-REST-ff1709?style=for-the-badge&logo=django&logoColor=white&color=ff1709&labelColor=gray)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)

# Setup

#### ⚠️Caution: The setting and installation steps can vary depending on the user; this was just an example guideline.


The current version has been tested on the following system configurations:
* Ubuntu ^22.04
* Python ^3.11
* Django ^4.2.7
* PostgreSQL ^16

## Prerequisites

 - [Install Redis on Linux](https://redis.io/docs/install/install-redis/install-redis-on-linux/)

 - Install PostgreSQL using the following example command on Ubuntu/Debian systems: 
    ```bash
    sudo apt-get install postgresql 
    ```
    Start the PostgreSQL service:
    ```bash
    sudo service postgresql start
    ```
 - Set up a username and password for PostgreSQL. 
 
    Login and connect as the default user (postgres):
    ```bash
    sudo -u postgres psql
    ```
    Change the password:
    ```bash
    postgres=# ALTER USER postgres PASSWORD '123456';
    ```

 - Create a new (clean & empty) PostgreSQL database (e.g., covsonar) and edit settings accordingly  see [settings.py -> Databases](covsonar_backend/settings.py#L87))
    
    create new database
    ```bash
    postgres=# CREATE DATABASE covsonar;
    ```

 - Install the required dependencies, such as Python and Poetry.
 
    Create a new Python environment with Conda:

    ```bash
    conda create -n sonar-backend python=3.11 poetry
    conda activate sonar-backend
    ```
> [!note]
> **🗿 Recommended software:** DB Management Software (e.g. DBeaver), REST Client (e.g. Insomnia, Insomnia configuration can be shared)

## Install sonar-backend

1. Clone the Project:
    ```bash
    git clone https://github.com/rki-mf1/sonar-backend.git
    cd sonar-backend
    ```
2. Install Dependencies with Poetry:
    ```bash
    poetry install
    ```
Once these steps are completed, proceed to the next section.

## Setup sonar-backend (development server)

There is a "template.env" file in the root directory. This file contains variables that must be used in the program and may differ depending on the environment. Hence, The ".env.template" file should be copied and changed to ".env", and then the variables should be edited according to your system.

1. Check if the application and django are set up and running correctly.
    ```bash
    python manage.py 
    ```
    This will show a list of commands and options that can be used with manage.py.

2. Start database migration (create the tables in the database)
    ```bash
    python manage.py migrate
    ```

3. Start application
    ```bash
    python manage.py runserver
    ```
    You can access the application at `http://127.0.0.1:8000/`.


### Sublineage Search (optional, SARS-CoV-2 specific)

To enable sublineage search for SARS-CoV-2, you must first import the Parent-Child relationship. Use the following command to download the latest version of lineages from [cov-lineages/pango-designation](https://github.com/cov-lineages/pango-designation/) and  import it into the database automatically:

```bash
python manage.py import_lineage
```

If you have a specific file from pangoline that you manually downloaded, you can specify it using the following command:

```bash
python manage.py import_lineage --lineages test-data/lineages_2024_01_15.csv --alias-key test-data/alias_key_2024_01_15.json
```

### **Note:** 
 - `manage.py` is used for all django commands
 - `python .\manage.py migrate` commits all migration db changes to the database. also creates django specific administrative tables 
 - `python .\manage.py createsuperuser` creates a user with full access to all db operations and to the admin page
 - `python .\manage.py runapscheduler` starts the appscheduler, which then enables jobs (as of now used for imports, see below). can be canceled after running, as of now only used to setup the jobs for manual use.
 - `python .\manage.py runserver` starts the development server. in 99% of cases no restart is needed to apply changes to the django code. While running, the terminal will output any api requests and `print` statements. exceptions will not be printed automatically.

### Misc
 - Access dev. admin page should be reached under [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) for login see `createsuperuser` above
- To reset the entire database, use the command:
  ```bash
  python manage.py flush
  ```
  If you only want to reset the tables related to the Sonar database, use:
  ```bash
  python manage.py flush_sonarDB
  ```
 - During development, we use [Insomnia](https://insomnia.rest/) for API testing. To facilitate testing, we provide the API collection in the file `resource/Insomnia_XXXX.json`. The datasets can be found under the `test-data` folder. You can easily import the collection into your Insomnia API client and start testing."

### Test Datasets

We provide the test datasets under the `test-data` directory. These datasets can be used in `sonar-backend` commands and Insomnia API for testing.

| File                       | Usage                                        |
|----------------------------|----------------------------------------------|
| `alias_key.json`           | Used in the `python manage.py import_lineage` command.                    |
| `lineages.zip`             | Used in the `python manage.py import_lineage` command.                    |
| `lineages.ready.tsv`        | Example output from the `import_lineage` command.                          |
| `covid19.180.tsv`           | Input sample containing  meta information (tsv). |
| `cache_180_mafft.zip`       | Input sample containing the genomic sequence (fasta) using MAFFT aligner. |
| `MN908947.3.gbk`            | Reference genome of SARS-CoV-2 in GenBank format.                          |
| `dump-sonar-test-db.sql`| SQL dump files, an easy way to test by importing the SQL file into the database for testing and working with pytest."                    |


## Setup sonar-backend (production)

### Without Docker
...

### Deploy sonar-backend with Docker in Linux environment (experimental)
Prerequisite is you have to [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
These commands and Docker files are tested on Docker version 25.0.2.

1. Build the sonar-backend image
```bash
docker build -t backend_dev:local -f Dockerfile .
```
2. Start Docker compose
```bash
docker compose -f "docker-compose-dev.yml" up  --build 
```
OR use -d to detach the command. For example:
```bash
docker-compose -f "docker-compose-dev.yml" up --build -d
```
3. List the containers
```bash
docker ps
```
you should see something like:
```bash
CONTAINER ID   IMAGE                         COMMAND                  CREATED          STATUS          PORTS                            NAMES
efae00c34d0b   sonar-backend-backend-nginx   "/docker-entrypoint.…"   11 minutes ago   Up 11 minutes   80/tcp, 0.0.0.0:8000->8000/tcp   sonar-backend-backend-nginx-1     
d721ec159ec8   backend_dev:local             "python manage.py ru…"   11 minutes ago   Up 11 minutes   0.0.0.0:59571->9080/tcp          dev-covsonar-django
fbc301efe63d   postgres:alpine               "docker-entrypoint.s…"   11 minutes ago   Up 11 minutes   0.0.0.0:59574->5432/tcp          dev-covsonar-db
8b125b974c65   redis:7                       "docker-entrypoint.s…"   11 minutes ago   Up 11 minutes   127.0.0.1:6379->6379/tcp         dev-covsonar-cache
```
4. Set up Database
```bash
docker compose -f docker-compose-dev.yml exec  dev-django python manage.py migrate
```
Once the containers are up and running, you can access the backend via http://127.0.0.1:8000/api for sonar-cli or http://127.0.0.1:8000/admin through a web browser.

----

# License

This project is licensed under....

# Acknowledgments

This tool is built upon the foundations of covsonar and pathosonar projects.

Special thanks to all sonar contributors...

## Open Tasks:
- lineages table and filter
- mutation annotations POS = ANN[*.EFFECT] = annotation_type
- property exclude


### genome querying

#### URL [api]/samples/genomes/
#### Parameters
| Parameter     | type | description                                       |
|---------------|------|---------------------------------------------------|
| filters       | s.b. | filters that will we be used to query the samples |
| showNX        | bool | tbd                                               |
| vcf_format    | bool | tbd                                               |

#### Filters 

The *filters* parameter sent to the endpoint must be a valid JSON containing a basic filter (see below) or "andFilter" and/or "orFilter":
- "andFilter" is a list of basic filters like explained below.
- "orFilter" is a list of basic filters or objects, that must contain further "andFilter"- or "orFilter"-objects

On the most basic level, a filter must contain the following parameters:
- A "label": used to determine the type of the filter, e.g. "Property", "SNP Nt" or "SNP AA", this is used, to choose the filtering method in the viewset
- Parameters of the filtering method: these will be used by the method as keyword arguments, so they must have the exact same names as the filtering methods
- "*filter_type*" will most likely correspond to a [django field lookup](https://docs.djangoproject.com/en/dev/ref/models/querysets/#field-lookups), like "gte" (greater then equals)
- NOT filters can be done by giving the "*exclude*" parameter as True
#### Examples
Every letter stand for a complete basic filter, e.g.: 
```json
{
    "label": "Property",
    "property_name": "collection_date",
    "filter_type": "exact",
    "value": "2022-01-05"
}
```

- A:
```json
{
    "andFilter": ["A"]
}
```
- A && B:
```json
{
    "andFilter": ["A", "B"]
}
```

- (A && B) || C:
```json
{
    "andFilter": ["A", "B"],
    "orFilter": [
        {"andFilter": ["C"]}
    ]
}
```
also possible:
```json
{
    "andFilter": ["A", "B"],
    "orFilter": ["C"]
}
```

- A || B || C:
```json
{
    "andFilter": ["A"],
    "orFilter": [
        {"andFilter": ["B"]},
        {"andFilter": ["C"]}
        ]
}
```
also possible:
```json
{
    "orFilter": [
        "A","B","C"
    ]
}
```
- (A || B) && C
```json
{
    "andFilter": [
        { "orFilter": ["A","B"]},
        "C"
    ]
}
```
