# Setup

## Prerequisites

 - Install postgres

    example commnad in Ubuntu/Debian system.
    ```
    sudo apt-get install postgresql 
    ```
    start the service
    ```
    sudo service postgresql start
    ```
 - Setup username/password for postgres

    login and connect as default user (postgres)
    ```
    sudo -u postgres psql
    ```
    change the password
    ```
    postgres=# ALTER USER postgres PASSWORD '123456';
    ```

 - Setup a new (clean & empty) postgres DB (datbase name (e.g., covsonar) and edit settings accordingly, see [settings.py -> Databases](covsonar_backend/settings.py#L87))
    
    create new database
    ```
    postgres=# CREATE DATABASE covsonar;
    ```

 - Install requirements (e.g., python and poetry)

    install new python environment with conda
    ```
    conda create -n sonar-backend python=3.11 poetry
    conda activate sonar-backend
    ```
    
**🗿 Recommended software:** DB Management Software (e.g. DBeaver), REST Client (e.g. Insomnia, Insomnia configuration can be shared)

## Install sonar-backend

1. Clone the project
    ```
    git clone https://github.com/rki-mf1/sonar-backend.git
    cd sonar-backend
    ```
2. Install dependencies with poetry 
    ```
    poetry install
    ```

Once these steps are completed, you can move on to the next section.

## Setup Django (development server)

1. Check if the application and django are set up and running correctly.
    ```
    python manage.py 
    ```
    This will show a list of commands and options that can be used with manage.py.
2. Start database migration (create the table in the database)
    ```
    python manage.py migrate
    ```
3. Start application
    ```
    python manage.py runserver
    ```
    You can access the application at `http://127.0.0.1:8000/`.

Note:
 - `manage.py` is used for all django commands
 - `python .\manage.py migrate` commits all migration db changes to the database. also creates django specific administrative tables 
 - `python .\manage.py createsuperuser` creates a user with full access to all db operations and to the admin page
 - `python .\manage.py runapscheduler` starts the appscheduler, which then enables jobs (as of now used for imports, see below). can be canceled after running, as of now only used to setup the jobs for manual use.
 - `python .\manage.py runserver` starts the development server. in 99% of cases no restart is needed to apply changes to the django code. While running, the terminal will output any api requests and `print` statements. exceptions will not be printed automatically.

## Misc

 - dev admin page should be reached under [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) for login see createsuperuser above
 - reset(empty) the database with `python .\manage.py flush`

### TODO

## move todos to gitlab issues!

## Annotations
- region from where?

## DB Issues:
- mutation start and end are zero based index, label is 1 based index

## Open Tasks:
- lineages table and filter
- mutation annotations POS = ANN[*.EFFECT] = annotation_type
- property exclude
