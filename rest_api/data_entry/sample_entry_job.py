import pathlib
import time
from datetime import datetime
from rest_api.data_entry.sample_import import SampleImport
from rest_api.data_entry.sequence_job import clean_unused_sequences
from rest_api.models import (
    Alignment,
    AnnotationType,
    Mutation,
    Sample,
    Sequence,
    Mutation2Annotation,
)
from django.db import DataError
from django.db.utils import OperationalError
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
logger = get_task_logger(__name__)


# NOTE: This variable need to be adjustable.
_batch_size = 5

class SampleEntryJob:
    def run_data_entry(self):
        print("--- running data entry ---")
        files = list(
            pathlib.Path("import_data").joinpath("samples").glob("**/*.sample")
        )
        print(f"{len(files)} files found")
        timer = datetime.now()
        number_of_batches = len(files) // _batch_size
        print("Batch size:", _batch_size)
        print(f"Total number of batches: {number_of_batches}")
        files = [str(file) for file in files]
        if _batch_size:
            replicon_cache = {}
            gene_cache = {}
            for i in range(0, len(files), _batch_size):
                try:
                    batchtimer = datetime.now()
                    print(
                        f"processing batch {(i//_batch_size) + 1} of {number_of_batches}"
                    )
                    batch = files[i : i + _batch_size]
                    process_batch.delay(batch, replicon_cache, gene_cache)
                    print(
                        f"batch {(i//_batch_size) + 1} done in {datetime.now() - batchtimer}"
                    )
                except Exception as e:
                    print(f"Error in batch {(i//_batch_size) + 1}: {e}")
        print(f"import done in {datetime.now() - timer}")


@shared_task
def process_batch(batch: list[str], replicon_cache, gene_cache):
    try:
        sample_import_objs = [SampleImport(pathlib.Path(file)) for file in batch]
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
        annotations = []

        for sample_import_obj in sample_import_objs:
            annotations.extend(sample_import_obj.get_annotation_objs())
        with cache.lock("annotation"):
            AnnotationType.objects.bulk_create(
                annotations,
                ignore_conflicts=True,
            )
        annotation2mutations = []
        for sample_import_obj in sample_import_objs:
            annotation2mutations.extend(
                sample_import_obj.get_annotation2mutation_objs()
            )
        with cache.lock("annotation2mutation"):
            Mutation2Annotation.objects.bulk_create(
                annotation2mutations, ignore_conflicts=True
            )
        # Filter sequences without associated samples
        clean_unused_sequences()

    except DataError as data_error:
        # Handle the DataError exception here
        logger.error(f"DataError: {data_error}")
        # Perform additional error handling or logging as needed
        logger.error("Error happens on this batch")
        for sample_import_obj in sample_import_objs:
            logger.error(sample_import_obj.sample_file_path)
        raise
    except Exception as e:
        # Handle other exceptions if necessary
        logger.error(f"An unexpected error occurred: {e}")
        raise
