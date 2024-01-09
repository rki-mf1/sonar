#!/bin/bash
id
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER mate_pg_admin WITH PASSWORD 'mate_pg_pass';
    CREATE USER mate_staging_pg_admin;
    CREATE USER mate_pg_read;
    CREATE DATABASE mate;
    GRANT ALL PRIVILEGES ON DATABASE mate TO mate_pg_admin;
EOSQL


pg_restore -v -d mate /docker-entrypoint-initdb.d/pg_mate.dump