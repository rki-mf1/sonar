#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

    GRANT ALL PRIVILEGES ON DATABASE "$POSTGRES_DB" TO $POSTGRES_USER;
    ALTER DATABASE "$POSTGRES_DB" OWNER TO $POSTGRES_USER;
EOSQL

PGPASSWORD=$POSTGRES_PASSWORD

# psql -U "$POSTGRES_USER" "$POSTGRES_DB" < docker-entrypoint-initdb.d/dump-sonar-test-db.sql && echo $'\n -- Import database is complete --'
