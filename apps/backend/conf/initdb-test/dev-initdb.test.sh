#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
       IF NOT EXISTS ( SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='$POSTGRES_USER') THEN
          CREATE ROLE $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';
          RAISE NOTICE '$POSTGRES_USER user successfully created';
       ELSE
          RAISE NOTICE '$POSTGRES_USER user already exists';
       END IF;
    END\$\$;

    ALTER ROLE $POSTGRES_USER CREATEDB;
    SELECT 'CREATE DATABASE $POSTGRES_DB'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$POSTGRES_DB')\gexec
    GRANT ALL PRIVILEGES ON DATABASE "$POSTGRES_DB" TO $POSTGRES_USER;
    ALTER DATABASE "$POSTGRES_DB" OWNER TO $POSTGRES_USER;
EOSQL

PGPASSWORD=$POSTGRES_PASSWORD
# psql -U "$POSTGRES_USER" "$POSTGRES_DB" < docker-entrypoint-initdb.d/dump-sonar-test-db.sql && echo $'\n -- Import database is complete --'
