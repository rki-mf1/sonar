#!/usr/bin/env bash

xz -d -k "../covid19/SARS-COV2_12.tsv.xz"
xz -d -k "../covid19/SARS-COV2_12.fasta.xz"
cd ../../backend

./scripts/linux/clean-dev-env.sh -r -d -t


cd ../cli
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate ./env

sonar-cli add-ref --gb ../test_data/covid19//MN908947.nextclade.gb
sonar-cli import -r MN908947.3 --fasta "../test_data/covid19/SARS-COV2_12.fasta" --cache /sonar/data/import -t 7 --method 1  --auto-anno --no-skip
sonar-cli add-prop --name age --descr "Age" --dtype value_integer
sonar-cli add-prop --name sequencing_reason --descr "Sampling reason" --dtype value_varchar
sonar-cli add-prop --name euro --descr "Price" --dtype value_float
sonar-cli add-prop --name sample_type --descr "Sample Type" --dtype value_varchar
sonar-cli add-prop --name comments --descr "Comments" --dtype value_varchar
sonar-cli import -r MN908947.3 -t 7 --tsv "../test_data/covid19/SARS-COV2_12.tsv" --cols name=name  collection_date=collection_date sequencing_tech=sequencing_tech lab=lab zip_code=zip_code lineage=lineage sample_type=sample_type comments=comments age=age euro=euro sequencing_reason=sequencing_reason

sonar-cli import-lineage -l ../test_data/covid19/lineages_2024_01_15_full.tsv

#dump sql database




rm "../test_data/covid19/SARS-COV2_12.tsv"
rm "../test_data/covid19/SARS-COV2_12.fasta"

cd ../backend

# add to processing_job table: (job_name, status):
# cli_failed-job	F
# cli_queue-job	Q

# dump mit COPY and store conf/docker/initdb-test dump-sonar-12-test-db.sql
