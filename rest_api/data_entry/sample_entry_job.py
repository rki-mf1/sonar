import os
import pathlib
from datetime import datetime
import shutil
import zipfile
import traceback
from covsonar_backend.settings import REDIS_URL, SAMPLE_BATCH_SIZE, SONAR_DATA_ARCHIVE, SONAR_DATA_ENTRY_FOLDER, SONAR_DATA_PROCESSING_FOLDER
from rest_api.data_entry.sample_import import SampleImport
from rest_api.data_entry.annotation_import import AnnotationImport
from rest_api.models import (
    Alignment,
    AnnotationType,
    Mutation,
    Sample,
    Sequence,
    Mutation2Annotation,
    ImportLog,
)
from django.db import DataError
from celery import shared_task, group
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.db import transaction
import environ

logger = get_task_logger(__name__)



def check_for_new_data():
    processing_dir = pathlib.Path(SONAR_DATA_PROCESSING_FOLDER)
    # processing_dir.mkdir(parents=True, exist_ok=True)

    zip_files = list(pathlib.Path(SONAR_DATA_ENTRY_FOLDER).glob("*.zip"))

    if zip_files:
        print("# New data found")
        for file in zip_files:
            print(f"## Processing {file}")
            # create name file with processing dir (move to SONAR_DATA_PROCESSING_FOLDER)
            new_path = file.rename(processing_dir.joinpath(file.name))
            import_archive(new_path)
        check_for_new_data()

def import_archive(process_file_path: pathlib.Path):
    try:
        temp_dir = (
            pathlib.Path(SONAR_DATA_ARCHIVE)
            .joinpath("temp")
            .joinpath(process_file_path.stem)
        )
        print(f"## Unzip to {temp_dir}")
        # unzip the zip file to SONAR_DATA_ARCHIVE
        with zipfile.ZipFile(process_file_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        print(f"--- running data entry for {temp_dir} ---")
        sample_files = list(temp_dir.joinpath("samples").glob("**/*.sample"))
        anno_files = list(temp_dir.joinpath("anno").glob("**/*.vcf"))
        print(f"Sample: {len(sample_files)} files found")
        print(f"Annotation (vcfs): {len(anno_files)} files found")
        timer = datetime.now()
        batch_size = SAMPLE_BATCH_SIZE

        number_of_batches = (len(sample_files) + batch_size - 1 )// batch_size if sample_files else (len(anno_files)+ batch_size - 1) // batch_size

        print("Batch size:", batch_size)
        print(f"Total number of batches: {number_of_batches}")
        sample_files = [str(file) for file in sample_files]
        if batch_size:
            replicon_cache = {}
            gene_cache = {}
            if REDIS_URL:
                print("setting up sample import celery jobs..")
                sample_jobs = []
                for i in range(0, len(sample_files), batch_size):
                    batch = sample_files[i : i + batch_size]
                    sample_jobs.append(
                        process_batch.s(
                            batch, replicon_cache, gene_cache, str(temp_dir)
                        )
                    )
                results = group(sample_jobs).apply_async().get()
                for result in results:
                    if not result[0]:
                        raise Exception(
                            f"Sample Import Error: {result[1]} - {result[2]}"
                        )
                results = (
                    group([process_annotation.s(str(file)) for file in anno_files])
                    .apply_async()
                    .get()
                )
                for result in results:
                    if not result[0]:
                        raise Exception(
                            f"Annotation Import Error: {result[1]} - {result[2]}"
                        )
            else:
                print("--------------- WARNING -----------------")
                print("REDIS_URL not set, running without celery.")
                print("This will take a long time.")
                print("--------------- ------- -----------------")
                replicon_cache = {}
                gene_cache = {}
                for i in range(0, len(sample_files), batch_size):
                    try:
                        batchtimer = datetime.now()
                        batch = sample_files[i : i + batch_size]
                        print(
                            f"processing batch {(i//batch_size) + 1} of {number_of_batches}"
                        )
                        process_batch_single_thread(
                            batch, replicon_cache, gene_cache, str(temp_dir)
                        )
                        print(
                            f"batch {(i//batch_size) + 1} done in {datetime.now() - batchtimer}"
                        )
                    except Exception as e:
                        print(f"Error in batch {(i//batch_size) + 1}: {e}")
        print(f"import done in {datetime.now() - timer}")
    except Exception as e:
        print(f"Error in import_archive: {e}")
        error_dir = pathlib.Path(SONAR_DATA_ARCHIVE).joinpath("error")
        error_dir.mkdir(parents=True, exist_ok=True)
        process_file_path.rename(error_dir.joinpath(process_file_path.name))
        ImportLog.objects.create(
            type=ImportLog.ImportType.SAMPLE_ANNOTATION_ARCHIVE,
            file=process_file_path,
            success=False,
            exception_text=e,
            stack_trace=traceback.format_exc(),
        )
    else:
        completed_dir = pathlib.Path(SONAR_DATA_ARCHIVE).joinpath("completed")
        completed_dir.mkdir(parents=True, exist_ok=True)
        process_file_path.rename(completed_dir.joinpath(process_file_path.name))
        ImportLog.objects.create(
            type=ImportLog.ImportType.SAMPLE_ANNOTATION_ARCHIVE,
            file=process_file_path,
            success=True,
        )
    finally:
        shutil.rmtree(temp_dir)


@shared_task
def process_batch(batch: list[str], replicon_cache, gene_cache, temp_dir):
    try:
        sample_import_objs = [
            SampleImport(pathlib.Path(file), import_folder=temp_dir) for file in batch
        ]
        sequences = [
            sample_import_obj.get_sequence_obj()
            for sample_import_obj in sample_import_objs
        ]
        with cache.lock("sequence"):
            Sequence.objects.bulk_create(sequences, ignore_conflicts=True)
        samples = [
            sample_import_obj.get_sample_obj()
            for sample_import_obj in sample_import_objs
        ]
        with cache.lock("sample"):
            Sample.objects.bulk_create(
                samples,
                update_conflicts=True,
                unique_fields=["name"],
                update_fields=["sequence"],
            )
        [x.update_replicon_obj(replicon_cache) for x in sample_import_objs]
        alignments = [
            sample_import_obj.get_alignment_obj()
            for sample_import_obj in sample_import_objs
        ]
        with cache.lock("alignment"):
            Alignment.objects.bulk_create(alignments, ignore_conflicts=True)
        mutations = []
        for sample_import_obj in sample_import_objs:
            mutations.extend(sample_import_obj.get_mutation_objs(gene_cache))
        with cache.lock("mutation"):
            Mutation.objects.bulk_create(mutations, ignore_conflicts=True)
        mutations2alignments = []
        for sample_import_obj in sample_import_objs:
            mutations2alignments.extend(sample_import_obj.get_mutation2alignment_objs())
        with cache.lock("mutation2alignment"):
            Mutation.alignments.through.objects.bulk_create(
                mutations2alignments, ignore_conflicts=True
            )

        # Filter sequences without associated samples
        # clean_unused_sequences() #why?
        return (True, None, None)

    except Exception as e:
        # Handle the DataError exception here
        logger.error(f"DataError: {e}")
        # Perform additional error handling or logging as needed
        logger.error("Error happens on this batch")
        return (False, str(e), traceback.format_exc())


@shared_task
def process_annotation(file_name):
    try:
        annotation_import = AnnotationImport(file_name)
        with cache.lock("annotation"):
            AnnotationType.objects.bulk_create(
                annotation_import.get_annotation_objs(),
                ignore_conflicts=True,
            )
        with cache.lock("annotation2mutation"):
            Mutation2Annotation.objects.bulk_create(
                annotation_import.get_annotation2mutation_objs(), ignore_conflicts=True
            )
    except Exception as e:
        logger.error(f"Error in process_annotation: {e}")
        return (False, str(e), traceback.format_exc())
    return (True, None, None)


def process_batch_single_thread(batch, replicon_cache, gene_cache, temp_dir):
    try:
        sample_import_objs = [
            SampleImport(file, import_folder=temp_dir) for file in batch
        ]
        with transaction.atomic():
            sequences = [
                sample_import_obj.get_sequence_obj()
                for sample_import_obj in sample_import_objs
            ]

            Sequence.objects.bulk_create(sequences, ignore_conflicts=True)
            samples = [
                sample_import_obj.get_sample_obj()
                for sample_import_obj in sample_import_objs
            ]
            Sample.objects.bulk_create(
                samples,
                update_conflicts=True,
                unique_fields=["name"],
                update_fields=["sequence"],
            )
            [x.update_replicon_obj(replicon_cache) for x in sample_import_objs]
            alignments = [
                sample_import_obj.get_alignment_obj()
                for sample_import_obj in sample_import_objs
            ]
            Alignment.objects.bulk_create(alignments, ignore_conflicts=True)
            mutations = []
            for sample_import_obj in sample_import_objs:
                mutations.extend(sample_import_obj.get_mutation_objs(gene_cache))
            Mutation.objects.bulk_create(mutations, ignore_conflicts=True)
            mutations2alignments = []
            for sample_import_obj in sample_import_objs:
                mutations2alignments.extend(
                    sample_import_obj.get_mutation2alignment_objs()
                )
            Mutation.alignments.through.objects.bulk_create(
                mutations2alignments, ignore_conflicts=True
            )
            annotations = []

            for sample_import_obj in sample_import_objs:
                annotations.extend(sample_import_obj.get_annotation_objs())
            AnnotationType.objects.bulk_create(
                annotations,
                ignore_conflicts=True,
            )
            annotation2mutations = []
            for sample_import_obj in sample_import_objs:
                annotation2mutations.extend(
                    sample_import_obj.get_annotation2mutation_objs()
                )
            Mutation2Annotation.objects.bulk_create(
                annotation2mutations, ignore_conflicts=True
            )

            # Filter sequences without associated samples
            # clean_unused_sequences()

    except DataError as data_error:
        # Handle the DataError exception here
        print(f"DataError: {data_error}")
        # Perform additional error handling or logging as needed
        print("Error happens on this batch")
        for sample_import_obj in sample_import_objs:
            print(sample_import_obj.sample_file_path)
        raise
    except Exception as e:
        # Handle other exceptions if necessary
        print(f"An unexpected error occurred: {e}")
        raise
