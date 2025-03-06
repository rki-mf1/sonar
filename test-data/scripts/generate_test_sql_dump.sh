#!/usr/bin/env bash

xz -d -k "../sars-cov-2/SARS-CoV-2_12.tsv.xz"
xz -d -k "../sars-cov-2/SARS-CoV-2_12.fasta.xz"
cd ../../apps/backend

./scripts/linux/clean-dev-env.sh -d -t

cd ../cli
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate ./env

sonar-cli add-ref --gb ../../test-data/sars-cov-2/MN908947.nextclade.gb
# import sequences
sonar-cli import -r MN908947.3 --fasta ../../test-data/sars-cov-2/SARS-CoV-2_12.fasta -t 7 --method 1  --auto-anno --no-skip
# add properties to db
sonar-cli add-prop --name age --descr "Age" --dtype value_integer
sonar-cli add-prop --name sequencing_reason --descr "Sampling reason" --dtype value_varchar
sonar-cli add-prop --name euro --descr "Price" --dtype value_float
sonar-cli add-prop --name sample_type --descr "Sample Type" --dtype value_varchar
sonar-cli add-prop --name comments --descr "Comments" --dtype value_varchar
# import sample properties
sonar-cli import -r MN908947.3 -t 7 --tsv ../../test-data/sars-cov-2/SARS-CoV-2_12.tsv --cols name=name  collection_date=collection_date sequencing_tech=sequencing_tech lab=lab zip_code=zip_code lineage=lineage sample_type=sample_type comments=comments age=age euro=euro sequencing_reason=sequencing_reason
# import lineages
sonar-cli import-lineage -l ../../test-data/sars-cov-2/lineages_test.tsv

cd ../backend
# add to processing_job table: (job_name, status):
# cli_failed-job	F
# cli_queue-job	Q
echo "Insert jobs to processing_job table ..."
export $(grep -v '^\s*#' conf/docker/common.env | xargs)
export $(grep -v '^\s*#' conf/docker/dev-secrets.env | xargs)

PGPASSWORD=$POSTGRES_PASSWORD psql -h localhost -p 8432 -v ON_ERROR_STOP=1 --username $POSTGRES_USER --dbname $POSTGRES_DB <<EOSQL
    INSERT INTO processing_job (job_name, status, entry_time) VALUES ('cli_failed-job', 'F', CURRENT_TIMESTAMP);
    INSERT INTO processing_job (job_name, status, entry_time) VALUES ('cli_queue-job', 'Q', CURRENT_TIMESTAMP);
EOSQL

# dump mit COPY and store backend/conf/initdb-test dump-sonar-12-test-db.sql
DUMP_FILE="conf/initdb-test/dump-sonar-12-test-db.sql"
echo "Dump database to $DUMP_FILE"
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h localhost -p 8432 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"  --no-owner --no-acl --format=plain --file=$DUMP_FILE

# # remove unzipped tsv and fasta
rm "../../test-data/sars-cov-2/SARS-CoV-2_12.tsv"
rm "../../test-data/sars-cov-2/SARS-CoV-2_12.fasta"
