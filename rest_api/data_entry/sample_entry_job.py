from concurrent.futures import ThreadPoolExecutor
import pathlib
from datetime import date, datetime
from multiprocessing import Pool, cpu_count
from threading import Lock

import traceback

import django, json
from django.db import transaction
from django.db.utils import DataError

from rest_api.data_entry.sample_import import SampleImport
from rest_api.models import Alignment, AnnotationType, Mutation, Sample, Sequence

_debug = False  # set to True to run only one file
_async = True
_print_traceback = False
_batch_size = 50
global log_lock
log_lock = Lock()


# for actual multiprocessing, not needed rn
def async_init():
    django.setup()
    from django.db import connections

    connections.close_all()


class SampleEntryJob:
    def run_data_entry(self):
        print("--- running data entry ---")
        files = list(
            pathlib.Path("import_data").joinpath("samples").glob("**/*.sample")
        )
        print(f"{len(files)} files found")
        timer = datetime.now()
        if _batch_size:
            for i in range(0, len(files), _batch_size):
                print(f"Batch {i}")
                batch = files[i : i + _batch_size]
                for file in batch:
                    self.process_batch(batch)
        elif _debug:
            file_worker(files[0])
        elif _async:
            with ThreadPoolExecutor(cpu_count(), initializer=async_init) as p:
                p.map(file_worker, files),
                p.shutdown(wait=True)
        else:
            for file in files:
                file_worker(file)

        print(f"import done in {datetime.now() - timer}")

    def process_batch(self, batch):
        sample_import_objs = [SampleImport(file) for file in batch]
        replicon_cache = {}
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
                mutations.extend(sample_import_obj.get_mutation_objs())
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


def file_worker(file):
    try:
        with transaction.atomic():
            from rest_api.models import EnteredData

            if file.is_file():
                base_name = file.name
                if not EnteredData.objects.filter(
                    type="sample", name=base_name
                ).exists():
                    sample_import = None
                    try:
                        sample_import = SampleImport(file)
                        sample_import.write_to_db()
                        sample_import.move_files(success=True)
                    except Exception as e:
                        if sample_import:
                            sample_import.move_files(success=False)
                        raise e
                    else:
                        EnteredData.objects.create(
                            type="sample", name=base_name, date=datetime.now()
                        )
                else:
                    print("already imported ", file)
    except Exception as e:
        write_to_log(e, file)
    else:
        print("imported ", file)


def write_to_log(e, file):
    print(f"Error importing file: {file}: \n\t {e}")
    if _print_traceback:
        traceback.print_exc()
    log_path = f"import_data/logs/{date.today().isoformat()}_sample_error_import.log"
    global log_lock
    with log_lock:
        if not pathlib.Path(log_path).is_file():
            print("creating log file")
            pathlib.Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w") as f:
                json.dump({file: str(e)}, f)
            return
        current_data = json.loads(open(log_path, "r").read())
        current_data[file] = str(e)
        with open(log_path, "w") as f:
            json.dump(current_data, f)
