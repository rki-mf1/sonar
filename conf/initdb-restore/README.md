# Backup aus Prod in Lokaler Umgebung wiederherstellen
* Backup muss `pg_mate.dump` heißen und im Ordner `conf/initdb-restore` liegen
* `docker-compose -f docker-compose-from-dump.yml up`
* DB Settings in Django anpassen: 
  * Host ist `postgres-restored`
  * User ist `mate_pg_admin` 
  * Passwort ist `mate_pg_pass`

