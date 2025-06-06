import collections
import csv
from io import BytesIO
import json
import os
import pickle
import sys
import time
import traceback
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Union
import zipfile

from mpire import WorkerPool
import pandas as pd
from sonar_cli.align import sonarAligner
from sonar_cli.annotation import Annotator
from sonar_cli.api_interface import APIClient
from sonar_cli.basic import _check_property
from sonar_cli.basic import _check_reference
from sonar_cli.basic import _is_import_required
from sonar_cli.basic import _log_import_mode
from sonar_cli.basic import construct_query
from sonar_cli.cache import sonarCache
from sonar_cli.common_utils import _files_exist
from sonar_cli.common_utils import _get_csv_colnames
from sonar_cli.common_utils import calculate_time_difference
from sonar_cli.common_utils import clear_unnecessary_cache
from sonar_cli.common_utils import copy_file
from sonar_cli.common_utils import flatten_json_output
from sonar_cli.common_utils import flatten_list
from sonar_cli.common_utils import get_current_time
from sonar_cli.common_utils import get_fname
from sonar_cli.common_utils import out_autodetect
from sonar_cli.common_utils import read_var_parquet_file
from sonar_cli.config import ANNO_CHUNK_SIZE
from sonar_cli.config import ANNO_TOOL_PATH
from sonar_cli.config import BASE_URL
from sonar_cli.config import CHUNK_SIZE
from sonar_cli.config import KSIZE
from sonar_cli.config import PROP_CHUNK_SIZE
from sonar_cli.config import SCALED
from sonar_cli.logging import LoggingConfigurator
from sonar_cli.sourmash_ext import perform_search
from tqdm import tqdm

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()
bar_format = "{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]"


class sonarUtils:
    """
    A class used to perform operations on a Tool's.
    """

    def __init__(self):
        pass

    def get_default_reference_gb() -> str:
        """Gets the default reference GenBank file.
        Returns:
            str: Absolute path to the reference GenBank file.
        """
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "ref.gb"
        )

    # DATA IMPORT

    @staticmethod
    def import_data(  # noqa: C901
        db: str,
        nextclade_json: List[str] = [],
        fasta: List[str] = [],
        csv_files: List[str] = [],
        tsv_files: List[str] = [],
        prop_links: List[str] = [],
        cachedir: str = None,
        autolink: bool = False,
        auto_anno: bool = False,
        progress: bool = False,
        update: bool = False,
        threads: int = 1,
        quiet: bool = False,
        reference: str = None,
        method: int = 1,
        no_upload_sample: bool = False,
        include_nx: bool = True,
        debug: bool = False,
        must_pass_paranoid: bool = False,
    ) -> None:
        """Import data from various sources into the database.

        Args:
            db: The database to import into.
            fasta: List of fasta files to import.
            csv_files: List of CSV files to import.
            tsv_files: List of TSV files to import.
            prop_links: List of column to property links (formatted as col=prop) to consider for import.
            cachedir: The directory to use for caching data during import.
            autolink: Whether to automatically link data.
            progress: Whether to show a progress bar during import.
            update: Whether to update existing records. (False = Update )
            threads: The number of threads to use for import.
            quiet: Whether to suppress logging.
        """
        _log_import_mode(update, quiet)
        reference = _check_reference(db, reference)
        start_import_time = get_current_time()
        # checks
        nextclade_json = nextclade_json or []
        fasta = fasta or []
        tsv_files = tsv_files or []
        csv_files = csv_files or []
        _files_exist(*nextclade_json, *fasta, *tsv_files, *csv_files)
        if not _is_import_required(nextclade_json, fasta, tsv_files, csv_files, update):
            LOGGER.info("Nothing to import.")
            sys.exit(0)

        # property handling
        # NOTE:
        # In the future, we need to edit/design the code to
        # be more flexible when managing newly added properties.

        properties = {}
        if prop_links:
            # construct property dcit from file header or user provide
            properties = sonarUtils._get_prop_names(
                prop_links=prop_links,
                autolink=autolink,
                csv_files=csv_files,
                tsv_files=tsv_files,
            )
            if "name" not in properties:
                LOGGER.error(
                    "Cannot link ID. Please provide a mapping ID in the meta file, add '--cols name=(column ID/sample name)' to the command line."
                )
                sys.exit(1)
            sample_id_column = properties["name"]
        else:
            # if prop_links is not provide but csv/tsv given....
            if csv_files or tsv_files:
                LOGGER.error(
                    "Cannot link ID. Please provide a mapping ID in the meta file, add --cols name=(column ID/sample name) to the command line."
                )
                sys.exit(1)
        # setup cache
        cache = sonarUtils._setup_cache(
            db=db,
            reference=reference,
            cachedir=cachedir,
            update=update,
            progress=progress,
            debug=debug,
            include_nx=include_nx,
            auto_anno=auto_anno,
        )

        # importing sequences
        if fasta and not nextclade_json:
            # Segment genome detection
            if cache.cluster_db is not None:
                for fname in fasta:
                    new_path = copy_file(fname, cache.blast_dir)
                    best_alignments = perform_search(
                        new_path,
                        cache.cluster_db,
                        KSIZE,
                        SCALED,
                    )

                    cache.blast_best_aln[fname] = best_alignments
                    # print(cache.blast_best_aln)

                    # rm new_path the copied file
                    os.remove(new_path)
                LOGGER.info(
                    f"[runtime] Assign Reference: {calculate_time_difference(start_import_time, get_current_time())}"
                )

            sonarUtils._import_fasta(
                fasta,
                cache,
                threads,
                progress,
                method,
                no_upload_sample,
                must_pass_paranoid,
            )
        elif fasta and nextclade_json:
            LOGGER.info("Importing Nextclade JSON files.")
            sonarUtils.nextclade_import(
                fasta,
                nextclade_json,
                cache,
                threads,
                progress=progress,
                no_upload_sample=no_upload_sample,
            )

        # importing properties
        if csv_files or tsv_files:
            if len(properties) == 0:
                LOGGER.warning(
                    "Skip sending properties: no column in the file is mapped to the corresponding variables in the database."
                )
            else:
                if not no_upload_sample:
                    sonarUtils._import_properties(
                        sample_id_column,
                        properties,
                        csv_files,
                        tsv_files,
                        progress=progress,
                    )

        end_import_time = get_current_time()
        LOGGER.info(
            f"[runtime] Import total: {calculate_time_difference(start_import_time, end_import_time)}"
        )
        LOGGER.info(f"---- Done: {end_import_time} ----\n")
        cache.logfile_obj.write(
            f"[runtime] Import total: {calculate_time_difference(start_import_time, end_import_time)}\n"
        )
        cache.logfile_obj.write(f"---- Done: {end_import_time} ----\n")
        cache.logfile_obj.close()
        cache.error_logfile_obj.write(f"---- Done: {end_import_time} ----\n")
        cache.error_logfile_obj.close()
        cache.__exit__(None, None, None)

    @staticmethod
    def _setup_cache(
        db: str = None,
        reference: str = None,
        cachedir: Optional[str] = None,
        update: bool = True,
        progress: bool = False,
        debug: bool = False,
        include_nx: bool = True,
        auto_anno: bool = False,
    ) -> sonarCache:
        """Set up a cache for sequence data."""
        # Instantiate a sonarCache object.
        return sonarCache(
            db,
            outdir=cachedir,
            logfile="import.log",
            allow_updates=update,
            temp=not cachedir,
            debug=debug,
            disable_progress=not progress,
            refacc=reference,
            include_nx=include_nx,
            auto_anno=auto_anno,
        )

    @staticmethod
    def nextclade_import(  # noqa: C901
        fasta_files: List[str],
        nextclade_json: List[str],
        cache: sonarCache,
        threads: int = 1,
        progress: bool = False,
        no_upload_sample: bool = False,
    ):
        if not no_upload_sample:
            json_resp = APIClient(base_url=BASE_URL).get_jobID()
            job_id = json_resp["job_id"]

        if not fasta_files:
            return

        start_seqcheck_time = get_current_time()
        sample_data_dict_list = cache.add_fasta_v2(*fasta_files, chunk_size=CHUNK_SIZE)
        prepare_seq_time = calculate_time_difference(
            start_seqcheck_time, get_current_time()
        )
        LOGGER.info(f"[runtime] Sequence check: {prepare_seq_time}\n")
        cache.logfile_obj.write(f"[runtime] Sequence check: {prepare_seq_time}\n")
        LOGGER.info(f"Total input samples: {cache.sampleinput_total}")

        # Map Nextclade JSON files and Fasta files (sequence names)
        start_align_time = get_current_time()
        passed_samples_list = cache.add_nextclade_json(
            *nextclade_json, data_dict_list=sample_data_dict_list, chunk_size=100
        )
        LOGGER.info(
            f"Numer of samples that passed Nextclade JSON mapping: {len(passed_samples_list)}"
        )
        LOGGER.info(
            f"[runtime] JSON mapping: {calculate_time_difference(start_align_time, get_current_time())}"
        )
        cache.logfile_obj.write(
            f"[runtime] JSON mapping: {calculate_time_difference(start_align_time, get_current_time())}\n"
        )

        # SKIP PARANOID TEST
        # NOTE: because now we skip N and some deletion insetion mutations
        # cannot be matched with parent_id

        n = ANNO_CHUNK_SIZE
        passed_samples_chunk_list = [
            tuple(
                list(passed_samples_list[i : i + n]),
            )
            for i in range(0, len(passed_samples_list), n)
        ]
        if cache.auto_anno:
            anno_result_list = []
            start_anno_time = get_current_time()
            try:
                with WorkerPool(
                    n_jobs=threads,
                    start_method="fork",
                    shared_objects=cache,
                    pass_worker_id=True,
                    use_worker_state=False,
                ) as pool:
                    pool.set_shared_objects(cache)
                    raw_anno_result_list = pool.map_unordered(
                        sonarUtils.annotate_sample,
                        passed_samples_chunk_list,
                        progress_bar=True,
                        progress_bar_options={
                            "position": 0,
                            "desc": "Annotate samples...",
                            "unit": "chunks",
                            "bar_format": bar_format,
                        },
                    )
                    # Flatten the list of lists into a single list
                    anno_result_list = flatten_list(raw_anno_result_list)
            except Exception as e:
                tb = traceback.format_exc()
                LOGGER.error(
                    f"Annotation process failed with error: {e}, abort all workers. Traceback:\n{tb}"
                )
                # Abort all pool workers
                pool.terminate()  # Or pool.close()
                sys.exit(1)  # raise # Re-raise to stop the program entirely

            LOGGER.info(
                f"[runtime] Sample annotation: {calculate_time_difference(start_anno_time, get_current_time())}"
            )
            cache.logfile_obj.write(
                f"Sample anno usage time: {calculate_time_difference(start_anno_time, get_current_time())}\n"
            )

        else:
            LOGGER.info("Skipping annotation step.")

        # Send Result over network.
        if not no_upload_sample:
            start_upload_time = get_current_time()
            # NOTE: reuse the chunk size from anno
            # n = 500
            LOGGER.info(
                "Uploading and importing sequence mutation profiles into backend..."
            )
            cache_dict = {"job_id": job_id}
            for chunk_number, sample_chunk in enumerate(passed_samples_chunk_list, 1):
                LOGGER.debug(f"Uploading chunk {chunk_number}.")
                sonarUtils.zip_import_upload_sample_singlethread(
                    cache_dict, sample_chunk, chunk_number
                )
            # Wait for all chunk to be processed
            incomplete_chunks = set(range(1, len(passed_samples_chunk_list)))
            while len(incomplete_chunks) > 0:
                chunks_tmp = incomplete_chunks.copy()
                for chunk_number in chunks_tmp:
                    job_with_chunk = f"{job_id}_chunk{chunk_number}"
                    resp = APIClient(base_url=BASE_URL).get_job_byID(job_with_chunk)
                    job_status = resp["status"]
                    if job_status in ["Q", "IP"]:
                        next
                    if job_status == "F":
                        LOGGER.error(
                            f"Job {job_with_chunk} failed (status={job_status}). Aborting."
                        )
                        sys.exit(1)
                    if job_status == "C":
                        incomplete_chunks.remove(chunk_number)
                if len(incomplete_chunks) > 0:
                    LOGGER.debug(
                        f"Waiting for {len(incomplete_chunks)} chunks to finish being processed."
                    )
                    sleep_time = 3
                    time.sleep(sleep_time)

            if cache.auto_anno:
                for chunk_number, each_file in enumerate(
                    tqdm(
                        anno_result_list,
                        desc="Uploading and importing annotations",
                        unit="file",
                        bar_format=bar_format,
                        position=0,
                        disable=not progress,
                    )
                ):
                    sonarUtils.zip_import_upload_annotation_singlethread(
                        cache_dict, each_file, chunk_number
                    )

            LOGGER.info(
                f"[runtime] Upload and import: {calculate_time_difference(start_upload_time, get_current_time())}"
            )
            cache.logfile_obj.write(
                f"[runtime] Upload and import: {calculate_time_difference(start_upload_time, get_current_time())}\n"
            )
            LOGGER.debug("Job ID: %s", job_id)
        else:
            LOGGER.info("Disable sending samples.")
        start_clean_time = get_current_time()
        clear_unnecessary_cache(passed_samples_list, threads)
        LOGGER.info(
            f"[runtime] Clear cache: {calculate_time_difference(start_clean_time, get_current_time())}"
        )

    @staticmethod
    def _import_fasta(  # noqa: C901
        fasta_files: List[str],
        cache: sonarCache,
        threads: int = 1,
        progress: bool = False,
        method: int = 1,
        no_upload_sample: bool = False,
        must_pass_paranoid: bool = False,
    ) -> None:
        """
        Process and import sequences from fasta files.

        Args:
            fasta_files: List of paths to fasta files.
            properties: Dictionary of properties linked to sample names.
            cache: Instance of sonarCache.
            threads: Number of threads to use for processing.
            progress: Whether to show progress bar.
            method: Alignment method 1 MAFFT, 2 Parasail, 3 WFA2-lib
        """
        if not no_upload_sample:
            json_resp = APIClient(base_url=BASE_URL).get_jobID()
            job_id = json_resp["job_id"]

        if not fasta_files:
            return
        start_seqcheck_time = get_current_time()
        sample_data_dict_list = cache.add_fasta_v2(
            *fasta_files, method=method, chunk_size=CHUNK_SIZE
        )
        prepare_seq_time = calculate_time_difference(
            start_seqcheck_time, get_current_time()
        )
        LOGGER.info(f"[runtime] Sequence check: {prepare_seq_time}\n")
        cache.logfile_obj.write(f"[runtime] Sequence check: {prepare_seq_time}\n")
        LOGGER.info(f"Total input samples: {cache.sampleinput_total}")

        # Align sequences and process
        aligner = sonarAligner(
            cache_outdir=cache.basedir,
            method=method,
            allow_updates=cache.allow_updates,
            debug=cache.debug,
        )
        l = cache._samplefiles_to_profile
        LOGGER.info(f"Total samples that need to be processed: {l}")
        if l == 0:
            return
        start_align_time = get_current_time()
        passed_align_samples = []
        with (
            WorkerPool(n_jobs=threads, start_method="fork") as pool,
            tqdm(
                desc="Profiling sequences...",
                total=l,
                unit="seqs",
                bar_format="{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]",
                disable=not progress,
            ) as pbar,
        ):
            try:
                for sample_data in pool.imap_unordered(
                    aligner.process_cached_sample, sample_data_dict_list
                ):
                    try:
                        if sample_data:  # Ignore None results
                            passed_align_samples.append(sample_data)
                        pbar.update(1)
                    except Exception as e:
                        LOGGER.error(
                            f"Error processing sample: {sample_data}\nException: {e}"
                        )
                        sys.exit(1)
            except Exception as outer_exception:
                LOGGER.error(f"Error in multiprocessing pool: {outer_exception}")
                sys.exit(1)
        LOGGER.info(
            f"Number of samples that passed alignment: {len(passed_align_samples)}"
        )
        LOGGER.info(
            f"[runtime] Alignment: {calculate_time_difference(start_align_time, get_current_time())}"
        )
        cache.logfile_obj.write(
            f"[runtime] Alignment: {calculate_time_difference(start_align_time, get_current_time())}\n"
        )

        start_paranoid_time = get_current_time()
        passed_samples_list = cache.perform_paranoid_cached_samples(
            passed_align_samples, must_pass_paranoid
        )
        LOGGER.info(
            f"[runtime] Paranoid test: {calculate_time_difference(start_paranoid_time, get_current_time())}"
        )
        cache.logfile_obj.write(
            f"Paranoid test usage time: {calculate_time_difference(start_paranoid_time, get_current_time())}\n"
        )
        n = ANNO_CHUNK_SIZE
        passed_samples_chunk_list = [
            tuple(
                list(passed_samples_list[i : i + n]),
            )
            for i in range(0, len(passed_samples_list), n)
        ]
        if cache.auto_anno:
            anno_result_list = []
            start_anno_time = get_current_time()
            try:
                with WorkerPool(
                    n_jobs=threads,
                    start_method="fork",
                    shared_objects=cache,
                    pass_worker_id=True,
                    use_worker_state=False,
                ) as pool:
                    pool.set_shared_objects(cache)
                    raw_anno_result_list = pool.map_unordered(
                        sonarUtils.annotate_sample,
                        passed_samples_chunk_list,
                        progress_bar=True,
                        progress_bar_options={
                            "position": 0,
                            "desc": "Annotate samples...",
                            "unit": "chunks",
                            "bar_format": bar_format,
                        },
                    )
                    # Flatten the list of lists into a single list
                    anno_result_list = flatten_list(raw_anno_result_list)
            except Exception as e:
                tb = traceback.format_exc()
                LOGGER.error(
                    f"Annotation process failed with error: {e}, abort all workers. Traceback:\n{tb}"
                )
                # Abort all pool workers
                pool.terminate()  # Or pool.close()
                sys.exit(1)  # raise # Re-raise to stop the program entirely

            LOGGER.info(
                f"[runtime] Sample annotation: {calculate_time_difference(start_anno_time, get_current_time())}"
            )
            cache.logfile_obj.write(
                f"Sample anno usage time: {calculate_time_difference(start_anno_time, get_current_time())}\n"
            )

        else:
            LOGGER.info("Skipping annotation step.")

        # Send Result over network.
        if not no_upload_sample:
            start_upload_time = get_current_time()
            # NOTE: reuse the chunk size from anno
            # n = 500
            LOGGER.info(
                "Uploading and importing sequence mutation profiles into backend..."
            )
            cache_dict = {"job_id": job_id}
            for chunk_number, sample_chunk in enumerate(passed_samples_chunk_list, 1):
                LOGGER.debug(f"Uploading chunk {chunk_number}.")
                sonarUtils.zip_import_upload_sample_singlethread(
                    cache_dict, sample_chunk, chunk_number
                )
            # Wait for all chunk to be processed
            incomplete_chunks = set(range(1, len(passed_samples_chunk_list)))
            while len(incomplete_chunks) > 0:
                chunks_tmp = incomplete_chunks.copy()
                for chunk_number in chunks_tmp:
                    job_with_chunk = f"{job_id}_chunk{chunk_number}"
                    resp = APIClient(base_url=BASE_URL).get_job_byID(job_with_chunk)
                    job_status = resp["status"]
                    if job_status in ["Q", "IP"]:
                        next
                    if job_status == "F":
                        LOGGER.error(
                            f"Job {job_with_chunk} failed (status={job_status}). Aborting."
                        )
                        sys.exit(1)
                    if job_status == "C":
                        incomplete_chunks.remove(chunk_number)
                if len(incomplete_chunks) > 0:
                    LOGGER.debug(
                        f"Waiting for {len(incomplete_chunks)} chunks to finish being processed."
                    )
                    sleep_time = 3
                    time.sleep(sleep_time)

            if cache.auto_anno:
                for chunk_number, each_file in enumerate(
                    tqdm(
                        anno_result_list,
                        desc="Uploading and importing annotations",
                        unit="file",
                        bar_format=bar_format,
                        position=0,
                        disable=not progress,
                    )
                ):
                    sonarUtils.zip_import_upload_annotation_singlethread(
                        cache_dict, each_file, chunk_number
                    )

            LOGGER.info(
                f"[runtime] Upload and import: {calculate_time_difference(start_upload_time, get_current_time())}"
            )
            cache.logfile_obj.write(
                f"[runtime] Upload and import: {calculate_time_difference(start_upload_time, get_current_time())}\n"
            )
            LOGGER.debug("Job ID: %s", job_id)
        else:
            LOGGER.info("Disable sending samples.")
        start_clean_time = get_current_time()
        clear_unnecessary_cache(passed_samples_list, threads)
        LOGGER.info(
            f"[runtime] Clear cache: {calculate_time_difference(start_clean_time, get_current_time())}"
        )

    @staticmethod
    def zip_import_upload_annotation_singlethread(
        shared_objects: dict, file_path, chunk_number: int
    ):
        # Create a zip file without writing to disk
        compressed_data = BytesIO()
        with zipfile.ZipFile(compressed_data, "w", zipfile.ZIP_LZMA) as zipf:
            # Find the index of 'var'
            path_parts = file_path.split("/")
            _index = path_parts.index("anno")
            # Join the parts starting from 'var'
            rel_path = "/".join(path_parts[_index:])

            zipf.write(file_path, arcname=rel_path)

        compressed_data.seek(0)

        files = {
            "zip_file": compressed_data,
        }

        job_id = shared_objects["job_id"]
        job_with_chunk = f"{job_id}_chunk{chunk_number}"
        LOGGER.debug(f"Uploading mutation annotations (job_id: {job_with_chunk})")
        json_response = APIClient(base_url=BASE_URL).post_import_upload(
            files, job_id=job_with_chunk
        )
        msg = json_response["detail"]
        if msg != "File uploaded successfully":
            LOGGER.error(msg)

    @staticmethod
    def zip_import_upload_sample_singlethread(
        shared_objects: dict, sample_list, chunk_number: int
    ):
        """Bundle up the data to be sent to the backend and send it"""

        files_to_compress = []
        for kwargs in sample_list:
            var_parquet_file = kwargs["var_parquet_file"]
            sample_dict = kwargs

            # Serialize the sample dictionary to bytes
            sample_bytes = pickle.dumps(sample_dict)

            # Append the serialized sample dictionary to the files to compress
            files_to_compress.append(
                (
                    f"samples/{get_fname(kwargs['name'], extension='.sample', enable_parent_dir=True)}",
                    sample_bytes,
                )
            )
            files_to_compress.append(var_parquet_file)

        # Create a zip file without writing to disk
        compressed_data = BytesIO()
        with zipfile.ZipFile(compressed_data, "w", zipfile.ZIP_LZMA) as zipf:
            for file_path in files_to_compress:
                if isinstance(file_path, tuple):
                    # Add the dictionary data to the archive with pickle extension
                    zipf.writestr(file_path[0], file_path[1])
                else:
                    # Find the index of 'var'
                    path_parts = file_path.split("/")
                    var_index = path_parts.index("var")
                    # Join the parts starting from 'var'
                    rel_path = "/".join(path_parts[var_index:])

                    zipf.write(file_path, arcname=rel_path)

        compressed_data.seek(0)

        files = {
            "zip_file": compressed_data,
        }
        job_id = shared_objects["job_id"]
        job_with_chunk = f"{job_id}_chunk{chunk_number}"
        LOGGER.debug(f"Uploading mutation profiles (job_id: {job_with_chunk})")
        json_response = APIClient(base_url=BASE_URL).post_import_upload(
            files, job_id=job_with_chunk
        )
        LOGGER.debug(f"Uploading job_id: {job_with_chunk} -- done")
        msg = json_response["detail"]
        if msg != "File uploaded successfully":
            LOGGER.error(msg)

    @staticmethod
    def _import_properties(  # noqa: C901
        sample_id_column: str,
        properties: Dict[str, Dict[str, str] | str],
        csv_files: List[str],
        tsv_files: List[str],
        progress: bool,
    ):
        """
        Imports properties to the database in a single request by zipping all files in memory.

        Args:
            sample_id_column: Column name for sample IDs.
            properties: A dictionary of properties where the key is a sample name, and the value is another dictionary of properties for that sample.
            csv_files: List of CSV files to include.
            tsv_files: List of TSV files to include.
            progress: If True, displays a progress bar.
        """
        start_time = get_current_time()

        all_files = tsv_files + csv_files
        job_ids = []

        filtered_properties = {k: v for k, v in properties.items() if k != "name"}
        columns_to_use = list(filtered_properties.keys()) + [sample_id_column]
        # Create an in-memory ZIP file
        for _file in all_files:
            LOGGER.info(f"Processing file: {_file}")
            file_extension = os.path.splitext(_file)[-1].lower()

            # Use pandas to read the file in chunks and process it
            chunk_iter = pd.read_csv(
                _file,
                sep="\t" if file_extension == ".tsv" else ",",
                dtype="string",
                chunksize=PROP_CHUNK_SIZE,
                usecols=columns_to_use,
            )
            chunk_num = 0
            for chunk in tqdm(
                chunk_iter, desc=f"Processing {_file} in chunks", disable=not progress
            ):
                chunk_num += 1
                zip_buffer = (
                    BytesIO()
                )  # f'/mnt/c/works/tmp/_import_properties/{chunk_num}.zip'  # BytesIO()

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_LZMA) as zip_file:
                    # Create a temporary in-memory file for the chunk
                    chunk_filename = (
                        f"{os.path.basename(_file)}_chunk_{chunk_num}{file_extension}"
                    )
                    csv_buffer = BytesIO()

                    # Write the chunk to the in-memory buffer
                    chunk.to_csv(
                        csv_buffer,
                        index=False,
                        sep="\t" if file_extension == ".tsv" else ",",
                    )
                    csv_buffer.seek(0)

                    # Add the in-memory CSV/TSV to the ZIP archive
                    arcname = f"{file_extension[1:]}/{chunk_filename}"
                    zip_file.writestr(arcname, csv_buffer.getvalue())

                # Ensure we seek back to the beginning of the buffer
                zip_buffer.seek(0)

                # Prepare data for the API call
                job_id = APIClient(base_url=BASE_URL).get_jobID(is_prop_job=True)[
                    "job_id"
                ]
                file = {"zip_file": ("properties.zip", zip_buffer, "application/zip")}
                data = {
                    "sample_id_column": sample_id_column,
                    "column_mapping": json.dumps(filtered_properties),
                    "job_id": job_id,
                }

                # Send the chunk to the backend
                json_response = APIClient(base_url=BASE_URL).post_import_upload(
                    data=data, files=file
                )

                msg = json_response.get("detail", "Unknown error")
                if msg != "File uploaded successfully":
                    LOGGER.error(msg)
                    return
                else:
                    job_ids.extend([job_id])
        # Final status checking
        LOGGER.info(f"All chunks for job {job_id} uploaded. Monitoring job status...")
        job_status = None
        sleep_time = 2

        # Wait for all chunk to be processed
        incomplete_jobs = set(job_ids)
        while len(incomplete_jobs) > 0:
            # We make a copy because we can't modify a set that is being
            # iterated through
            jobs_tmp = incomplete_jobs.copy()
            for job in jobs_tmp:
                resp = APIClient(base_url=BASE_URL).get_job_byID(job)
                job_status = resp["status"]
                if job_status in ["Q", "IP"]:
                    next
                if job_status == "F":
                    LOGGER.error(f"Job {job} failed (status={job_status}). Aborting.")
                    sys.exit(1)
                if job_status == "C":
                    incomplete_jobs.remove(job)
            if len(incomplete_jobs) > 0:
                LOGGER.debug(
                    f"Waiting for {len(incomplete_jobs)} chunks to finish being processed."
                )
                time.sleep(sleep_time)

        time_diff = calculate_time_difference(start_time, get_current_time())
        if job_status == "F":
            LOGGER.error(f"Job {job_id} is {job_status}: {time_diff}")
        else:
            LOGGER.info(f"[runtime] Job {job_id} is {job_status}: {time_diff}")

    @staticmethod
    def _get_prop_names(  # noqa: C901
        prop_links: List[str],
        autolink: bool,
        csv_files: List[str],
        tsv_files: List[str],
    ) -> Dict[str, str]:
        """
        Get property names based on user input.

        "--auto-link" will link columns in the file to existing properties
        in the database (no new property names will be created in the database).
        However, if the properties that the user manually inputs don't exist,
        we give a warning or (optional TODO: add those as new properties to the database).

        Parameters:
        - prop_links (List[str]): List of property links provided by the user.
        - autolink (bool): Flag to enable automatic linking of columns to existing properties.
        - csv_files (List[str]): List of CSV files to process.
        - tsv_files (List[str]): List of TSV files to process.

        Returns:
        - Dict[str, str]: Dictionary mapping column names to property details.

        Note:
            "name" key is special case, we use this to link the sample ID.
        """
        propnames = {}

        listofkeys, values_listofdict = sonarUtils.get_all_properties()
        prop_df = pd.DataFrame(values_listofdict, columns=listofkeys)

        # get column names from the files
        file_tuples = [(x, ",") for x in csv_files] + [(x, "\t") for x in tsv_files]
        col_names_fromfile = {}
        for fname, delim in file_tuples:
            col_names_fromfile[fname] = _get_csv_colnames(fname, delim)
        if autolink:
            LOGGER.info(
                "Auto-link is enabled, automatically linking columns in the file to existing properties in the database."
            )
            # Case insensitive linking (SAMPLE_TYPE = sample_type)
            for fname, col_names in col_names_fromfile.items():
                for col_name in col_names:
                    _row_df = prop_df[
                        prop_df["name"].str.fullmatch(col_name, na=False, case=False)
                    ]

                    if not _row_df.empty:
                        query_type = _row_df["query_type"].values[0]
                        name = _row_df["name"].values[0]
                        default = _row_df["default"].values[0]
                        propnames[col_name] = {
                            "db_property_name": name,
                            "data_type": query_type,
                            "default": default,
                        }

            # Handle sample ID linking
            for link in prop_links:
                prop, col = link.split("=")
                if prop.upper() == "NAME":
                    propnames["name"] = col

        else:
            LOGGER.info("Reading property names from user-provided '--cols'")
            for link in prop_links:
                if link.count("=") != 1:
                    LOGGER.error(
                        f"'{link}' is not a valid column-to-property assignment."
                    )
                    sys.exit(1)
                # Handle sample ID linking
                prop, col = link.split("=")
                if prop.upper() == "NAME":
                    propnames["name"] = col
                    continue

                _row_df = prop_df[
                    prop_df["name"].str.fullmatch(prop, na=False, case=False)
                ]
                if not _row_df.empty:
                    query_type = _row_df["query_type"].values[0]
                    default = _row_df["default"].values[0]
                    propnames[col] = {
                        "db_property_name": prop,
                        "data_type": query_type,
                        "default": default,
                    }
                else:
                    LOGGER.warning(
                        f"Property '{prop}' is unknown. Use 'list-prop' to see all valid properties or 'add-prop' to add it before import."
                    )
        # Check if columns exist in the provided CSV/TSV files
        # only existing columns shall pass
        valid_propnames = {}

        for col, prop_info in propnames.items():
            if col == "name":
                # Check if 'ID' exists in the provided CSV/TSV files
                valid_propnames[col] = prop_info
                id_column = prop_info
                missing_in_files = [
                    fname
                    for fname, cols in col_names_fromfile.items()
                    if id_column not in cols
                ]
                if missing_in_files:
                    LOGGER.error(
                        f"Mapping ID column '{id_column}' does not exist in the provided files: {', '.join(missing_in_files)}."
                    )
                    sys.exit(
                        1
                    )  # this will stop the whole prop-import process or just continue??
            else:
                missing_in_files = [
                    fname
                    for fname, cols in col_names_fromfile.items()
                    if col not in cols
                ]
                if not missing_in_files:
                    valid_propnames[col] = prop_info
                else:
                    LOGGER.warning(
                        f"Column '{col}' does not exist in the provided files: {', '.join(missing_in_files)}."
                    )

        propnames = valid_propnames

        LOGGER.info("Displaying property mappings:")
        LOGGER.info("(Input table column name -> Sonar database property name)")

        for prop, prop_info in propnames.items():
            if prop == "name":
                LOGGER.info(f"{prop_info} -> {prop}")
                continue
            db_property_name = prop_info.get("db_property_name", "N/A")
            LOGGER.info(f"{prop} -> {db_property_name}")
        LOGGER.info("--------")

        return propnames

    @staticmethod
    def annotate_sample(  # noqa: C901
        worker_id, shared_objects: sonarCache, *sample_list
    ):  # **kwargs):
        """
        NOTE: The _unique_name will be changed if the sample_list size changed or
        sample's name changed, so the exist checking will be fail.

        kwargs are sample dict object
        """
        try:
            cache = shared_objects
            # refmol = cache.default_refmol_acc
            input_vcf_dict = collections.defaultdict(
                list
            )  # Group VCFs by replicon accession
            # map_name_annovcf_dict = {}
            _unique_name = ""
            generated_files = []  # Collect all generated files
            # export_vcf:
            for kwargs in sample_list:
                _unique_name = _unique_name + kwargs["name"]
                replicon_accession = kwargs["refmol"]
                input_vcf_dict[replicon_accession].append(kwargs["vcffile"])
                if cache.allow_updates is False:
                    if os.path.exists(kwargs["vcffile"]):
                        continue

                sonarUtils.export_vcf(
                    cursor=kwargs,
                    cache=cache,
                    reference=replicon_accession,
                    outfile=kwargs["vcffile"],
                    from_var_file=True,
                )
                # for split vcf
                # map_name_annovcf_dict[kwargs["name"]] = kwargs["anno_vcf_file"]

            annotator = Annotator(
                annotator_exe_path=ANNO_TOOL_PATH,
                cache=cache,
            )
            # Annotate each group of VCFs by replicon accession
            for replicon_accession, vcf_files in input_vcf_dict.items():
                merged_vcf = os.path.join(
                    cache.anno_dir,
                    get_fname(f"{_unique_name}_{replicon_accession}", extension=".vcf"),
                )
                merged_anno_vcf = os.path.join(
                    cache.anno_dir,
                    get_fname(
                        f"{_unique_name}_{replicon_accession}", extension=".anno.vcf"
                    ),
                )
                filtered_vcf = os.path.join(
                    cache.anno_dir,
                    get_fname(
                        f"{_unique_name}_{replicon_accession}",
                        extension=".filtered.anno.vcf.gz",
                    ),
                )

                generated_files.append(filtered_vcf)
                if cache.allow_updates is False:
                    if os.path.exists(filtered_vcf):
                        return filtered_vcf

                # Merge VCFs if there are multiple files
                if len(vcf_files) == 1:
                    merged_vcf = vcf_files[0]
                else:
                    annotator.bcftools_merge(
                        input_vcfs=vcf_files, output_vcf=merged_vcf
                    )

                # #  check if it is already exist
                # # NOTE WARN: this doesnt check if the file is corrupt or not, or completed information in the vcf file.
                # if cache.allow_updates is False:
                #     if os.path.exists(kwargs["anno_vcf_file"]):
                #         return

                # Annotate the merged VC
                annotator.snpeff_annotate(
                    merged_vcf,
                    merged_anno_vcf,
                    replicon_accession,
                )
                annotator.bcftools_filter(merged_anno_vcf, filtered_vcf)

                # dont forget to change the name
                # split vcf back
                # annotator.bcftools_split(
                #     input_vcf=merged_anno_vcf,
                #     map_name_annovcf_dict=map_name_annovcf_dict,
                # )
                # clean unncessery file
                if os.path.exists(merged_vcf):
                    os.remove(merged_vcf)
                if os.path.exists(merged_anno_vcf):
                    os.remove(merged_anno_vcf)

        except Exception as e:
            tb = traceback.format_exc()
            LOGGER.error(f"Worker {worker_id} stopped: {e}. Traceback: {tb}")
            raise  # Raise to ensure the failure is propagated back to the worker pool
        return generated_files

    # MATCHING
    @staticmethod
    def match(
        db: str = None,
        profiles: List[str] = [],
        samples: List[str] = [],
        properties: Dict[str, str] = {},
        reference: Optional[str] = None,
        outfile: Optional[str] = None,
        output_column: Optional[List[str]] = [],
        format: str = "csv",
        showNX: bool = False,
        annotation_type: List[str] = [],
        annotation_impact: List[str] = [],
        ignore_terminal_gaps: bool = True,
        frameshifts_only: bool = False,
        exclude_annotation: bool = False,
        with_sublineage: bool = False,
        defined_props: Optional[List[Dict[str, str]]] = [],
    ):
        """
        Perform match operation and export the results.

        Args:
            db: Database name.
            profiles: List of profiles.
            samples: List of samples.
            properties: Dictionary of properties.
            reference: Reference accession.
            outfile: Output file path.
            output_column: List of output columns.
            format: Output format.
            showNX: Flag indicating whether to show NX.
            ignore_terminal_gaps: Flag indicating whether to terminal gaps.
            frameshifts_only: Flag indicating whether to only show frameshifts.

        Returns:
            None.
        """
        reference = _check_reference(db, reference)
        default_columns = _check_property(db, output_column)
        # if not reference:
        #    reference = dbm.get_default_reference_accession()
        #    LOGGER.info(f"Using Default Reference: {reference}")

        params = {}
        # params["filters"] = (
        #     '{"andFilter":[{"label":"Property","property_name":"sequencing_reason","filter_type":"exact","value":"N"}],"orFilter":[]}'
        # )

        params["filters"] = json.dumps(
            construct_query(
                reference=reference,
                profiles=profiles,
                properties=properties,
                defined_props=defined_props,
                with_sublineage=with_sublineage,
                samples=samples,
                annotation_type=annotation_type,
                annotation_impact=annotation_impact,
            )
        )

        params["reference_accession"] = reference
        params["showNX"] = showNX
        params["vcf_format"] = True if format == "vcf" else False

        if format == "count":
            params["limit"] = 1
        else:
            # hack (to get all result by using max bigint)
            params["limit"] = 999999999999999999
        params["offset"] = 0

        LOGGER.debug(params["filters"])

        json_response = APIClient(
            base_url=BASE_URL
        ).get_variant_profile_bymatch_command(params=params)
        LOGGER.info("Write outputs...")
        if "results" in json_response:
            rows = json_response
        else:
            LOGGER.error("server cannot return a result")
            sys.exit(1)  # or just return??

        sonarUtils._export_query_results(
            rows,
            format,
            reference,
            default_columns=default_columns,
            outfile=outfile,
            exclude_annotation=exclude_annotation,
            output_column=output_column,
        )

    @staticmethod
    def _export_query_results(
        cursor: object,
        format: str,
        reference: str,
        default_columns: List[str],
        outfile: Optional[str],
        exclude_annotation: bool = False,
        output_column: Optional[List[str]] = [],
    ):
        """
        Export results depending on the specified format.

        Args:
            cursor: Cursor object.
            format: Output format.
            reference: Reference accession.
            outfile: Output file path.

        Returns:
            None
        """
        if format in ["csv", "tsv"]:
            tsv = format == "tsv"
            cursor = flatten_json_output(cursor["results"], exclude_annotation)
            sonarUtils.export_csv(
                cursor,
                default_columns=default_columns,
                output_column=output_column,
                outfile=outfile,
                na="*** no match ***",
                tsv=tsv,
            )
        elif format == "count":
            count = cursor["count"]
            if outfile:
                with open(outfile, "w") as handle:
                    handle.write(str(count))
            else:
                print(count)
        elif format == "vcf":
            sonarUtils.export_vcf(
                cursor,
                reference=reference,
                outfile=outfile,
                na="*** no match ***",
            )
        else:
            LOGGER.error(f"'{format}' is not a valid output format")
            sys.exit(1)

    @staticmethod
    def export_csv(
        data: Union[List[Dict[str, Any]], Iterator[Dict[str, Any]]],
        default_columns: List[str],
        output_column: Optional[List[str]] = [],
        outfile: Optional[str] = None,
        na: str = "*** no data ***",
        tsv: bool = False,
    ) -> None:
        """
        Export the results of a SQL query or a list of rows into a CSV file.

        Parameters:
        data: An iterator over the rows of the query result, or a list of rows.
        default_columns: List of default columns to use if output_column is not provided.
        output_column: List of specific columns to output. If None, default_columns are used.
        outfile: The path to the output file. If None, the output is printed to stdout.
        na: The string to print when no data is available.
        tsv: If True, the output is formatted as a TSV (Tab-Separated Values) file. Otherwise, it is formatted as a CSV (Comma-Separated Values) file.
        """
        # Convert list data to an iterator

        if isinstance(data, list):
            data_iter = iter(data)
        else:
            data_iter = data

        try:
            first_row = next(data_iter)
        except StopIteration:
            LOGGER.info(na)
            first_row = None

        columns = output_column if output_column else default_columns

        with out_autodetect(outfile) as handle:
            try:
                sep = "\t" if tsv else ","
                writer = csv.DictWriter(
                    handle,
                    fieldnames=columns,
                    delimiter=sep,
                    lineterminator=os.linesep,
                )
                # Write the header regardless of whether we have rows
                writer.writeheader()
                # If there is no data, we return after writing the header
                if first_row is None:
                    return

                # Write the first row, selecting only the necessary columns
                writer.writerow({k: first_row.get(k, None) for k in columns})

                # Write the remaining rows
                for row in data_iter:
                    writer.writerow({k: row.get(k, None) for k in columns})
            except ValueError as e:
                LOGGER.error(f" error at row: {row}")
                LOGGER.error(e)
                raise
            except BrokenPipeError:
                pass

    # vcf
    @staticmethod
    def export_vcf(
        cursor: Optional[Union[dict, Any]] = None,
        reference: str = None,
        cache: sonarCache = None,
        outfile: Optional[str] = None,
        na: str = "*** no match ***",
        showNX: bool = False,
        from_var_file=False,
    ):  # noqa: C901
        """
        Exports data from a database result to a VCF file.

        Parameters:

        cursor: object
            if from_var_file is False
                The rows object which already has been fetched data.
            else if from_var_file is True


        reference: The reference genome name.
        outfile: The output file name. If None, output is printed to stdout.
        na: The string to print if there are no records.
        """
        if not cursor:
            LOGGER.info(na)
        else:
            # TODO: if we want to connect this function with match function
            # we have to put the condition to check the cursor type first.
            _dict = cache.refmols[reference]
            refernce_sequence = _dict["sequence"]

            if from_var_file:
                records, all_samples = _get_vcf_data_form_var_parquet_file(
                    cursor, refernce_sequence, showNX
                )
            else:
                records, all_samples = _get_vcf_data(cursor)

            if outfile is not None:
                directory_path = os.path.dirname(outfile)
                if directory_path and not os.path.exists(directory_path):
                    os.makedirs(directory_path, exist_ok=True)

            with out_autodetect(outfile) as handle:
                _write_vcf_header(handle, reference, all_samples)
                _write_vcf_records(handle, records, all_samples)

    @staticmethod
    def get_all_properties():
        json_response = APIClient(base_url=BASE_URL).get_all_properties()
        return json_response["keys"], json_response["values"]

    @staticmethod
    def get_all_references():
        rows = APIClient(base_url=BASE_URL).get_all_references()
        if not rows:
            return {"id": "", "accession": "", "taxon": "", "organism": ""}
        # only neccessary column
        modified_data = [
            {
                "id": entry["id"],
                "accession": entry["accession"],
                "taxon": entry["db_xref"],
                "organism": entry["organism"],
            }
            for entry in rows
        ]

        return modified_data

    @staticmethod
    def add_ref_by_genebank_file(reference_gbs: List[str]):
        """
        add reference
        """
        segment = False

        reference_gb_obj = []
        if len(reference_gbs) > 1:
            segment = True
            LOGGER.info(f"Detect segmented genome: {reference_gbs}")

        for reference_gb in reference_gbs:
            _files_exist(reference_gb)
            reference_gb_obj.append(open(reference_gb, "rb"))

        try:
            flag = APIClient(base_url=BASE_URL).post_add_reference(
                reference_gb_obj, segment
            )

            if flag:
                LOGGER.info("The reference has been added successfully.")
            else:
                LOGGER.error("The reference failed to be added.")
        except Exception as e:
            LOGGER.exception(e)
            LOGGER.error("Fail to process GeneBank file")
            raise

    @staticmethod
    def delete_reference(reference):
        LOGGER.info("Start to delete....the process is not reversible.")

        # delete only reference will also delete the whole linked data.
        # if samples_ids:
        #    if debug:
        #        logging.info(f"Delete: {samples_ids}")
        #    for sample in samples_ids:
        #        # dbm.delete_seqhash(sample["seqhash"])
        #        dbm.delete_alignment(
        #            seqhash=sample["seqhash"], element_id=_ref_element_id
        #        )

        json_response = APIClient(base_url=BASE_URL).post_delete_reference(reference)

        LOGGER.info(
            f"{json_response['samples_count']} alignments that are linked to the reference will also be deleted."
        )

    @staticmethod
    def delete_sample(reference: str = None, samples: List[str] = []) -> None:
        """
        Delete samples from the database.

        Args:
            db (str): The database to delete samples from.
            samples (list[str]): A list of samples to be deleted.  x

        NOTE: if we delete a sample, then all alignment that related
        to this sample will also deleted.
        """
        if len(samples) == 0:
            LOGGER.info("Nothing to delete.")

        json_response = APIClient(base_url=BASE_URL).post_delete_sample(
            reference, samples=samples
        )

        deleted = json_response["deleted_samples_count"]
        LOGGER.info(f"{deleted} of {len(samples)} samples found and deleted.")

        """

        LOGGER.info(f"{deleted} of {len(samples)} samples found and deleted.")
        LOGGER.info(f"{after_count} samples remain in the database.")
        """

    @staticmethod
    def add_property(
        name: str,
        datatype: str,
        querytype: str,
        description: str,
        subject: str,
        default: None,
        check_name: bool = True,
    ) -> int:
        data = {
            "name": name,
            "datatype": datatype,
            "querytype": querytype,
            "description": description,
            "default": default,
        }
        json_response = APIClient(base_url=BASE_URL).post_add_property(data)
        LOGGER.info(json_response["detail"])

    @staticmethod
    def delete_property(
        name: str,
    ) -> int:
        json_response = APIClient(base_url=BASE_URL).post_delete_property(name)
        LOGGER.info(json_response["detail"])


def _get_vcf_data_form_var_parquet_file(cursor: dict, selected_ref_seq, showNX) -> Dict:
    """
    Creates a data structure with records from a database cursor.

    Parameters:
    cursor: The cursor object from which to fetch data.

    Returns:
    records: A dictionary storing the genomic record data.
    all_samples: A sorted list of all unique samples in the records.
    """
    # Initialize the nested dictionary for storing records
    records = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(dict))
    )

    rows = read_var_parquet_file(
        cursor["var_parquet_file"], exclude_var_type="cds", showNX=showNX
    )
    sample_name = cursor["name"]
    all_samples = set(sample_name.split("\t"))

    for row in rows:
        try:
            if row["start"] - 1 < 0:
                pre_ref = ""
            else:
                pre_ref = selected_ref_seq[row["start"] - 1]
        except Exception as e:
            LOGGER.error(e)
            raise

        # Split out the data from each row
        chrom, pos, pre_ref, ref, alt, _ = (
            row["reference_acc"],
            row["start"],
            pre_ref,
            row["ref"],
            row["alt"],
            sample_name,
        )

        # POS position in VCF format: 1-based position
        pos = pos + 1
        # Skip the empty alternate values

        records[chrom][pos][ref][alt] = all_samples

        if "pre_ref" not in records[chrom][pos]:
            records[chrom][pos]["pre_ref"] = pre_ref

    return records, sorted(all_samples)


def _get_vcf_data(cursor) -> Dict:
    """
    Creates a data structure with records from a database cursor.

    Parameters:
    cursor: The cursor object from which to fetch data.

    Returns:
    records: A dictionary storing the genomic record data.
    all_samples: A sorted list of all unique samples in the records.
    """
    # Initialize the nested dictionary for storing records
    records = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(dict))
    )
    all_samples = set()

    for row in cursor:
        # Split out the data from each row
        chrom, pos, pre_ref, ref, alt, samples = (
            row["molecule.accession"],
            row["start"],
            row["pre_ref"],
            row["ref"],
            row["alt"],
            row["samples"],
        )

        # Convert the samples string into a set
        sample_set = set(samples.split("\t"))
        # POS position in VCF format: 1-based position
        pos = pos + 1
        # Skip the empty alternate values

        records[chrom][pos][ref][alt] = sample_set

        if "pre_ref" not in records[chrom][pos]:
            records[chrom][pos]["pre_ref"] = pre_ref
        # Update the list of all unique samples
        all_samples.update(sample_set)

    return records, sorted(all_samples)


def _write_vcf_header(handle, reference: str, all_samples: List[str]):
    """
    Writes the VCF file header to the given file handle.

    Parameters:
    handle: The file handle to which to write the header.
    reference: The reference genome name.
    all_samples: A list of all unique sample names.
    """
    handle.write("##fileformat=VCFv4.2\n")
    handle.write("##poweredby=sonar-cli\n")
    handle.write(f"##reference={reference}\n")
    handle.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n')
    handle.write(f"##contig=<ID={reference}>\n")
    handle.write(
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t"
        + "\t".join(all_samples)
        + "\n"
    )


def _write_vcf_records(handle, records: Dict, all_samples: List[str]):  # noqa: C901
    """
    Writes the VCF file records to the given file handle.

    Parameters:
    handle: The file handle to which to write the records.
    vcf_data: The dictionary storing the genomic record data.
    all_samples: A list of all unique sample names.
    """
    # Loop through each level of the dictionary to construct and write the VCF records
    for chrom in records:
        for pos in records[chrom]:
            for ref in records[chrom][pos]:
                if ref == "pre_ref":  # skip pre_ref key
                    continue
                # snps and inserts (combined output)
                alts = [x for x in records[chrom][pos][ref].keys() if x.strip()]
                if alts:
                    alt_samples = set()
                    gts = []
                    for alt in alts:
                        samples = records[chrom][pos][ref][alt]
                        alt_samples.update(samples)
                        gts.append(["1" if x in samples else "0" for x in all_samples])
                    gts = [
                        ["0" if x in alt_samples else "1" for x in all_samples]
                    ] + gts
                    record = [
                        chrom,
                        str(pos),
                        ".",
                        ref,
                        ",".join(alts),
                        ".",
                        ".",
                        ".",
                        "GT",
                    ] + ["/".join(x) for x in zip(*gts)]

                # dels (individual output)

                for alt in [
                    x for x in records[chrom][pos][ref].keys() if not x.strip()
                ]:
                    pre_ref = records[chrom][pos]["pre_ref"]
                    samples = records[chrom][pos][ref][alt]
                    record = [
                        chrom,
                        str(
                            1 if pos - 1 <= 0 else pos - 1
                        ),  # -1 to the position for DEL, NOTE: be careful for 0-1=-1
                        ".",
                        (pre_ref + ref),
                        (pre_ref) if alt == " " else alt,  # changed form '.'
                        ".",
                        ".",
                        ".",
                        "GT",
                    ] + ["0/1" if x in samples else "./." for x in all_samples]
                handle.write("\t".join(record) + "\n")
