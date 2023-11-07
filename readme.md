### Setup

## Prerequisites

 - install postgres
 - setup a new (clean & empty) postgres DB (name (covsonar) or edit settings accordingly, see [settings.py -> Databases](covsonar_backend/settings.py#L87))
 - install requirements (poetry)
 - recommended software: DB Management Software (e.g. DBeaver), REST Client (e.g. Insomnia, Insomnia configuration can be shared)

## Setup Django

 - `manage.py` is used for all django commands
 - `python .\manage.py migrate` commits all migration db changes to the database. also creates django specific administrative tables 
 - `python .\manage.py createsuperuser` creates a user with full access to all db operations and to the admin page
 - `python .\manage.py runapscheduler` starts the appscheduler, which then enables jobs (as of now used for imports, see below). can be canceled after running, as of now only used to setup the jobs for manual use.
 - `python .\manage.py runserver` starts the development server. in 99% of cases no restart is needed to apply changes to the django code. While running, the terminal will output any api requests and `print` statements. exceptions will not be printed automatically.

## Misc

 - dev admin page should be reached under [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) for login see createsuperuser above
 - reset(empty) the database with `python .\manage.py flush`

### TODO

## DB unique keys:
- mutation duplicates - enforce unique_together
- gene accession - enforce unique

## DB Issues:
- mutation start and end are zero based index, label is 1 based index
- remove mutation2property
- remove mutation frameshift
- gene cds accession
- gene cds symbol

## Open Tasks:
- lineages table and filter
- mutation annotations POS = ANN[*.EFFECT] = annotation_type
- exclude/q-object performance check
- property exclude


## Notes:
 - mutation - accession
 - type: nt replicon.accesison
 - type: cds gene gene_accession