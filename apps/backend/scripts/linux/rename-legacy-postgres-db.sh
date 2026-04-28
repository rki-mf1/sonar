#!/bin/sh
set -eu

legacy_db="${LEGACY_POSTGRES_DB:-covsonar}"
target_db="${POSTGRES_DB:-sonar}"
postgres_user="${POSTGRES_USER:-postgres}"
postgres_host="${POSTGRES_HOST:-localhost}"
postgres_port="${POSTGRES_PORT:-5432}"

if [ "$legacy_db" = "$target_db" ]; then
    echo "Legacy and target database names are identical; nothing to rename."
    exit 0
fi

export PGPASSWORD="${POSTGRES_PASSWORD:-}"

psql_args="
    --username=$postgres_user
    --host=$postgres_host
    --port=$postgres_port
    --dbname=postgres
    --tuples-only
    --no-align
"

legacy_exists="$(
    psql $psql_args --set=legacy_db="$legacy_db" <<'EOSQL'
SELECT 1
WHERE EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = :'legacy_db'
);
EOSQL
)"

target_exists="$(
    psql $psql_args --set=target_db="$target_db" <<'EOSQL'
SELECT 1
WHERE EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = :'target_db'
);
EOSQL
)"

if [ -n "$legacy_exists" ] && [ -n "$target_exists" ]; then
    echo "Both legacy database '$legacy_db' and target database '$target_db' exist. Refusing to rename automatically." >&2
    exit 1
fi

if [ -z "$legacy_exists" ]; then
    echo "Legacy database '$legacy_db' not found; nothing to rename."
    exit 0
fi

psql \
    --username="$postgres_user" \
    --host="$postgres_host" \
    --port="$postgres_port" \
    --dbname=postgres \
    --set=legacy_db="$legacy_db" \
    --set=target_db="$target_db" <<'EOSQL'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = :'legacy_db'
  AND pid <> pg_backend_pid();

SELECT format('ALTER DATABASE %I RENAME TO %I', :'legacy_db', :'target_db') \gexec
EOSQL

echo "Renamed legacy database '$legacy_db' to '$target_db'."
