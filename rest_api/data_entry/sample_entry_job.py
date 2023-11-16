from concurrent.futures import ThreadPoolExecutor
import pathlib
from datetime import datetime
from multiprocessing import Pool, cpu_count
import traceback

import django
from django.db import transaction

from rest_api.data_entry.sample_import import SampleImport

_debug = False   # set to True to run only one file
_async = True


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
        if _debug:
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
                        print(f"Error importing file: {base_name}: \n\t {e}\n")
                        raise e
                    else:
                        EnteredData.objects.create(
                            type="sample", name=base_name, date=datetime.now()
                        )
                else:
                    print("already imported ", file)
    except Exception as e:
        print(f"Error importing file: {file}: \n\t {e}\n")
        traceback.print_exc()
