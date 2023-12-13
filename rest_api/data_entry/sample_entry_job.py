import pathlib
from datetime import datetime
from django.db import transaction
from rest_api.data_entry.sample_import import SampleImport
from rest_api.models import Alignment, AnnotationType, Mutation, Sample, Sequence

# NOTE: This variable need to be adjustable.
_batch_size = 100

class SampleEntryJob:
    def run_data_entry(self):
        print("--- running data entry ---")
        files = list(
            pathlib.Path("import_data").joinpath("samples").glob("**/*.sample")
        )
        print(f"{len(files)} files found")
        timer = datetime.now()
        number_of_batches = len(files) // _batch_size + 1
        print(f"Total number of batches: {number_of_batches} of {_batch_size} batch size")
        if _batch_size:
            replicon_cache = {}
            gene_cache = {}
            for i in range(0, len(files), _batch_size):
                batchtimer = datetime.now()
                print(f"processing batch {(i//_batch_size) + 1} of {number_of_batches}")
                batch = files[i : i + _batch_size]
                self.process_batch(batch, replicon_cache, gene_cache)
                print(
                    f"batch {(i//_batch_size) + 1} done in {datetime.now() - batchtimer}"
                )
        print(f"import done in {datetime.now() - timer}")

    def process_batch(self, batch, replicon_cache, gene_cache):
        sample_import_objs = [SampleImport(file) for file in batch]
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
            Sample.objects.bulk_create(samples, ignore_conflicts=True)
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
