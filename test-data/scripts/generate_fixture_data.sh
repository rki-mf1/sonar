#!/usr/bin/env bash

# usage: ./generate_fixture_data.sh 10 OR ./generate_fixture_data.sh 1000

if [[ "$1" != "10" && "$1" != "1000" ]]; then
  echo "Error: Parameter must be either 10 or 1000."
  exit 1
fi

SUFFIX="$1"


xz -d -k "../sars-cov-2/SARS-COV-2_${SUFFIX}.tsv.xz"
xz -d -k "../sars-cov-2/SARS-COV-2_${SUFFIX}.fasta.xz"
cd ../../apps/backend

./scripts/linux/clean-dev-env.sh -d -t


cd ../cli
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate ./env

sonar-cli add-ref --gb ../../test-data/sars-cov-2/MN908947.nextclade.gb
sonar-cli import -r MN908947.3 --fasta "../../test-data/sars-cov-2/SARS-COV-2_${SUFFIX}.fasta" --cache /sonar/data/import -t 7 --method 1  --auto-anno --no-skip --skip-nx
sonar-cli add-prop --name sequencing_reason --descr "Sampling reason" --dtype value_varchar
sonar-cli add-prop --name isolation_source --descr "Isolation Source" --dtype value_varchar
sonar-cli import -r MN908947.3 -t 7 --tsv "../../test-data/sars-cov-2/SARS-COV-2_${SUFFIX}.tsv" --cols name=igs_id sequencing_reason=sequencing_reason isolation_source=isolation_source collection_date=date_of_sampling sequencing_tech=sequencing_platform lab=sequencing_lab.demis_lab_id zip_code=prime_diagnostic_lab.postal_code lineage=lineages
sonar-cli import-lineage -l ../../test-data/sars-cov-2/lineages_test.tsv

rm "../../test-data/sars-cov-2/SARS-COV-2_${SUFFIX}.tsv"
rm "../../test-data/sars-cov-2/SARS-COV-2_${SUFFIX}.fasta"

cd ../backend
# superuser
export $(grep -v '^\s*#' conf/docker/common.env | xargs)
export $(grep -v '^\s*#' conf/docker/dev-secrets.env | xargs)
PGPASSWORD=$POSTGRES_PASSWORD psql -h localhost -p 8432 -v ON_ERROR_STOP=1 --username $POSTGRES_USER --dbname $POSTGRES_DB <<EOSQL
    INSERT INTO auth_user (username, email, first_name, last_name, password, is_superuser, is_staff, is_active, date_joined)
    VALUES ('root', 'admin@example.com', 'admin', 'root', 'hashed_password', true, true, true, NOW());
EOSQL

./scripts/linux/dev-manage.sh dumpdata --indent=4 auth rest_api django_apscheduler -o "rest_api/fixtures/test_data_${SUFFIX}.json"

xz -f rest_api/fixtures/test_data_${SUFFIX}.json
