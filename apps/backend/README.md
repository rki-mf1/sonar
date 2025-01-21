# sonar-backend

The sonar-backend is web service that represents the API version of the Sonar tool (covsonar), which utilizes Django REST + PostgreSQL for scalability and integration with the web application.

![Static Badge](https://img.shields.io/badge/Lifecycle-Experimental-ff7f2a)

![Static Badge](https://img.shields.io/badge/Maintenance%20status-actively%20developed-brightgreen)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![DjangoREST](https://img.shields.io/badge/DJANGO-REST-ff1709?style=for-the-badge&logo=django&logoColor=white&color=ff1709&labelColor=gray)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)

**Please visit [sonar-backend wiki](https://github.com/rki-mf1/sonar-backend/wiki) for more details**

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
git clone https://github.com/rki-mf1/sonar-backend.git
cd sonar-backend
```

Next we need to set up secret information that will be unique to your installation. These values need to be defined in `sonar-backend/conf/docker/prod-secrets.env`. To see which values need to be set, you can check the `sonar-backend/conf/docker/dev-secrets.env` file but **do not just copy the values from this file**. You need to set your own passwords and Django SECRET_KEY.

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

If you want to deploy the frontend as well, you need to clone it:

```bash
git clone https://github.com/rki-mf1/sonar-frontend.git
cd sonar-frontend
```

Make sure you have npm installed (`conda create -n sonar-frontend nodejs` will work with conda), and then follow the frontend docs:

```
$ npm install
```

Next you probably want to customize the url of the sonar backend. You can set this from a file `sonar-frontend/.env.production` or directly from the command line when building the frontend:

```
$ VITE_SONAR_BACKEND_ADDRESS=https://myserver.com npm run build
```

Then copy the built files into the backend `work/` directory. You might need to tweak the commands below depending on the relative location of sonar-frontend and sonar-backend, and whether you are updating an existing copy of the frontend or doing this for the first time:

```
$ mkdir -p ../sonar-backend/work/frontend/dist
$ cp -r dist/* ../sonar-backend/work/frontend/dist
```

Now you should be able to access the frontend on your server at port 443 (e.g. `https://servername.org`).

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
$ git clone https://github.com/rki-mf1/sonar-backend.git
$ cd sonar-backend
```

Next, you can start up a dev instance of the software stack using docker compose (use the `-h` argument to see other options for this script):

```bash
$ ./scripts/linux/clean-dev-env.sh
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

| File                     | Usage                                                                                                                 |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `alias_key.json`         | Used in the `python manage.py import_lineage` command.                                                                |
| `lineages.zip`           | Used in the `python manage.py import_lineage` command.                                                                |
| `lineages.ready.tsv`     | Example output from the `import_lineage` command.                                                                     |
| `covid19.180.tsv`        | Input sample containing meta information (tsv).                                                                       |
| `cache_180_mafft.zip`    | Input sample containing the genomic sequence (fasta) using MAFFT aligner.                                             |
| `MN908947.3.gbk`         | Reference genome of SARS-CoV-2 in GenBank format.                                                                     |
| `dump-sonar-test-db-180-2025_01_21.INSERT.sql` | SQL dump files, an easy way to test by importing the SQL file into the database for testing and working with pytest." |

### Extra docker compose commands

1. Create superuser for Django admin

```bash
# docker-compose exec <service_name>, not docker-compose exec <container_name>.
./scripts/linux/dev-manage.sh createsuperuser
```

Once the containers are up and running, you can access

- sonar-cli reach the backend via http://127.0.0.1:8000/api
- http://127.0.0.1:8000/admin
- http://localhost:5555 for monitoring workers (username:"note" password:"123456")

---

# License

This project is licensed under....

# Acknowledgments

This tool is built upon the foundations of covsonar and pathosonar projects.

Special thanks to all sonar contributors...
