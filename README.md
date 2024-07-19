# sonar-backend

The sonar-backend is web service that represents the API version of the Sonar tool (covsonar), which utilizes Django REST + PostgreSQL for scalability and integration with the web application.

![Static Badge](https://img.shields.io/badge/Lifecycle-Experimental-ff7f2a)

![Static Badge](https://img.shields.io/badge/Maintenance%20status-actively%20developed-brightgreen)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) 
![DjangoREST](https://img.shields.io/badge/DJANGO-REST-ff1709?style=for-the-badge&logo=django&logoColor=white&color=ff1709&labelColor=gray)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)

#### Please visit [sonar-backend wiki](https://github.com/rki-mf1/sonar-backend/wiki) for more details

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

## Start sonar-backend (development server)

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
3. Start Redis server
    ```bash
    redis-server
    ```
4. Start Celery

    Navigate to the import folder. By default, if you do not specify in the .env file, the import_data folder will be created at the root level of snoar-backend.

    Then you have to run the following command in the terminal:
    ```bash
    celery -A covsonar_backend worker --loglevel=info --without-gossip --without-mingle --without-heartbeat -Ofair --concurrency=2 -E
    ```
    To access more detailed information about Celery, please visit the official Celery website at https://docs.celeryproject.org/en/latest/.

5. Start application
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


## Start sonar-backend with Docker 

### Deploy sonar-backend for development

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
docker compose -f "docker-compose-dev.yml" up --build -d
```

3. Create superuser for Django admin
```bash
# docker-compose exec <service_name>, not docker-compose exec <container_name>.
docker compose -f docker-compose-dev.yml exec dev-django python manage.py createsuperuser
```
Once the containers are up and running, you can access 
- sonar-cli reach the backend via http://127.0.0.1:8000/api
- http://127.0.0.1:8000/admin
- http://localhost:5555 for monitoring workers (username:"note" passwrod:"123456")

### Deploy sonar-backend with pre-built database for quickstart (used in GH action) (Linux environment)

```bash
docker compose -f "docker-compose.test-gh.yml" up  --build
```
Once the containers are up and running, you can access 
- sonar-cli reach the backend via http://127.0.0.1:8000/api
- http://127.0.0.1:8000/admin through a web browser (username:"note" passwrod:"123456")
- http://localhost:5555 for monitoring workers (username:"note" passwrod:"123456")

### Deploy sonar-backend for production
⚠️Caution: not a final version

1. Create an environment file.
```bash
cp template.env .prod.env
```

2. Create a config file for Nginx.
```bash
cp ./nginx/covsonar.conf ./nginx/prod.conf
```
3. Build local docker image
```bash
docker build -t backend:latest -f Dockerfile .
```
4. Start docker stacks
```bash
docker compose --env-file .prod.env  -f "docker-compose-prod.yml" up --build
```
5. Create super user for django admin
```bash
# docker-compose exec <service_name>, not docker-compose exec <container_name>.
docker compose --env-file .prod.env -f 'docker-compose-prod.yml' exec sonar-backend-django python manage.py createsuperuser
```


----

# License

This project is licensed under....

# Acknowledgments

This tool is built upon the foundations of covsonar and pathosonar projects.

Special thanks to all sonar contributors...
