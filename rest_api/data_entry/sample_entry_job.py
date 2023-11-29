from concurrent.futures import ThreadPoolExecutor
import pathlib
from datetime import date, datetime
from multiprocessing import Pool, cpu_count
from threading import Lock

import traceback

import django, json
from django.db import transaction

from rest_api.data_entry.sample_import import SampleImport

_debug = False  # set to True to run only one file
_async = True
_print_traceback = False
_batch_size = 100
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
            
        elif _debug:
            file_worker(files[0])
        elif _async:
            with ThreadPoolExecutor(cpu_count(), initializer=async_init) as p:
                p.map(file_worker, files)
                p.shutdown(wait=True)
        else:
            for file in files:
                file_worker(file)

        print(f"import done in {datetime.now() - timer}")


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
