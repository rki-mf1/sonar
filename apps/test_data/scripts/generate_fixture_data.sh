#!/usr/bin/env bash

# usage: ./generate_fixture_data.sh 10 OR ./generate_fixture_data.sh 1000

if [[ "$1" != "10" && "$1" != "1000" ]]; then
  echo "Error: Parameter must be either 10 or 1000."
  exit 1
fi

SUFFIX="$1"


xz -d -k "../covid19/SARS-COV2_${SUFFIX}.tsv.xz"
xz -d -k "../covid19/SARS-COV2_${SUFFIX}.fasta.xz"
cd ../../backend

./scripts/linux/clean-dev-env.sh -r -d -t


cd ../cli
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate ./env

sonar-cli add-ref --gb ../test_data/covid19//MN908947.nextclade.gb
sonar-cli import -r MN908947.3 --fasta "../test_data/covid19/SARS-COV2_${SUFFIX}.fasta" --cache /sonar/data/import -t 7 --method 1  --auto-anno --no-skip --skip-nx
sonar-cli add-prop --name sequencing_reason --descr "Sampling reason" --dtype value_varchar
sonar-cli add-prop --name isolation_source --descr "Isolation Source" --dtype value_varchar
sonar-cli import -r MN908947.3 -t 7 --tsv "../test_data/covid19/SARS-COV2_${SUFFIX}.tsv" --cols name=igs_id sequencing_reason=sequencing_reason isolation_source=isolation_source collection_date=date_of_sampling sequencing_tech=sequencing_platform lab=sequencing_lab.demis_lab_id zip_code=prime_diagnostic_lab.postal_code lineage=lineages
sonar-cli import-lineage -l ../test_data/covid19/lineages_test.tsv

rm "../test_data/covid19/SARS-COV2_${SUFFIX}.tsv"
rm "../test_data/covid19/SARS-COV2_${SUFFIX}.fasta"

cd ../backend
./scripts/linux/dev-manage.sh dumpdata --indent=4 rest_api django_apscheduler -o "rest_api/fixtures/test_data_${SUFFIX}.json"

xz -f rest_api/fixtures/test_data_${SUFFIX}.json
