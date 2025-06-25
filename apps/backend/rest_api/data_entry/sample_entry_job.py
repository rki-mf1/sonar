from datetime import datetime
import pathlib
import pickle
import shutil
import traceback
import zipfile

from celery import group
from celery import shared_task
from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist
from django.db import DataError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from line_profiler import LineProfiler
import pandas as pd

from covsonar_backend.settings import KEEP_IMPORTED_DATA_FILES
from covsonar_backend.settings import LOGGER
from covsonar_backend.settings import PROFILE_IMPORT
from covsonar_backend.settings import PROPERTY_BATCH_SIZE
from covsonar_backend.settings import REDIS_URL
from covsonar_backend.settings import SAMPLE_BATCH_SIZE
from covsonar_backend.settings import SONAR_DATA_ARCHIVE
from covsonar_backend.settings import SONAR_DATA_ENTRY_FOLDER
from covsonar_backend.settings import SONAR_DATA_PROCESSING_FOLDER
from rest_api import models
from rest_api.data_entry.annotation_import import AnnotationImport
from rest_api.data_entry.sample_import import SampleImport
from rest_api.models import Alignment
from rest_api.models import AminoAcidMutation
from rest_api.models import AnnotationType
from rest_api.models import FileProcessing
from rest_api.models import ImportLog
from rest_api.models import NucleotideMutation
from rest_api.models import ProcessingJob
from rest_api.models import Sample
from rest_api.models import Sequence
from rest_api.serializers import Sample2PropertyBulkCreateOrUpdateSerializer
from rest_api.utils import parse_date
from rest_api.utils import PropertyColumnMapping

property_cache = {}


def check_for_new_data():
    """Checks for new processing jobs in the database queue and processes them sequentially.
    Steps:
    - Fetches jobs with `QUEUED` status from the 'ProcessingJob' table, ordered by 'entry_time'.
    - For each job:
        - Retrieves associated files from 'FileProcessing'.
        - If an error occurs (files not found), updates job status to 'FAILED'.
        - Moves valid files to the processing directory.
        - Calls 'import_archive' to handle import logic.
    - Recursively calls itself to process subsequent jobs.

    """
    processing_dir = pathlib.Path(SONAR_DATA_PROCESSING_FOLDER)
    if REDIS_URL is None:
        print("--------------- WARNING -----------------")
        print("REDIS_URL not set, running without celery.")
        print("This will take a long time.")
        print("--------------- ------- -----------------")
    # only one worker (Master) can take a job at a time
    with transaction.atomic():
        # Fetch and lock a single job with QUEUED status NOTE: Order of entrytime is matter!!
        job = (
            ProcessingJob.objects.select_for_update()
            .filter(status=ProcessingJob.ImportType.QUEUED)
            .order_by("entry_time")
            .first()
        )
        if job is None:
            return
        # Update job status to IN_PROGRESS
        job.status = ProcessingJob.ImportType.IN_PROGRESS
        job.save()

    LOGGER.info(f"## New processing job: {job.job_name} ---")
    files = FileProcessing.objects.filter(processing_job=job)
    if not files.exists():
        LOGGER.warning(
            f"No associated files found, in {job.job_name}, marking as FAILED, continue the proces.."
        )
        job.status = ProcessingJob.ImportType.FAILED
        job.save()
        return

    for file in files:
        file_path = pathlib.Path(SONAR_DATA_ENTRY_FOLDER).joinpath(file.file_name)
        if not file_path.exists():
            LOGGER.error(f"File {file_path} does not exist, marking job as FAILED!")
            job.status = ProcessingJob.ImportType.FAILED
            job.save()
            return

        # move files to SONAR_DATA_PROCESSING_FOLDER
        if "_prop" in str(file_path):
            # Handle corresponding .pkl file for property imports
            pkl_file = file_path.with_suffix(".pkl")
            new_zip_path = file_path.rename(processing_dir.joinpath(file_path.name))
            new_pkl_path = pkl_file.rename(processing_dir.joinpath(pkl_file.name))
            import_archive(
                new_zip_path, pkl_path=new_pkl_path
            )  # Pass the .pkl path to import_archive
        else:
            # process as normal sample or annotation import
            new_zip_path = file_path.rename(processing_dir.joinpath(file_path.name))
            import_archive(new_zip_path)

    # Recursively check for new data after processing current batch
    check_for_new_data()
    print("---- No new jobs found. ----")


def import_archive(process_file_path: pathlib.Path, pkl_path: pathlib.Path = None):
    """Processes an archive file by extracting and importing its contents.
    Steps:
    - Determines the corresponding `ProcessingJob` based on the file.
    - Updates the job status to `IN_PROGRESS`.
    - Extracts the archive into a temporary directory.
    - Differentiates between property imports (requires `.pkl` mapping) and sample/annotation imports.
    - Uses Celery (if available) to process batches; otherwise, processes sequentially.
    - On success, moves files to `completed` directory or deletes them.
    - On failure, moves files to `error` directory and logs the error.
    - Updates the job status based on the completion of the processed file.

    NOTE: [optional] if it just starts, we update the ProcessingJob (to IP)
    """
    temp_dir = (
        pathlib.Path(SONAR_DATA_ARCHIVE)
        .joinpath("temp")
        .joinpath(process_file_path.stem)
    )
    try:

        filename_ID = process_file_path.name
        # get JOB ID based on the given files
        proJob_obj = ProcessingJob.objects.filter(files__file_name=filename_ID).first()
        if not proJob_obj:
            LOGGER.warning(
                "The given import files is not related to any jobID (skip this batch)"
            )
            return
        job_ID = proJob_obj.job_name
        LOGGER.info(f"Process job: {job_ID}")
        print(f"Unzip to {temp_dir}")
        # ProcessingJob.objects.filter(job_name=job_ID).update(
        #     status=ProcessingJob.ImportType.IN_PROGRESS
        # )
        # unzip the zip file to SONAR_DATA_ARCHIVE
        with zipfile.ZipFile(process_file_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        # Files are distributed and processed
        print(f"Running data entry for {temp_dir}")
        if pkl_path and pkl_path.exists():
            # property import
            import_type = ImportLog.ImportType.PROPERTY
            print(f"Property import detected")
            batch_size = PROPERTY_BATCH_SIZE
            print("Batch size:", batch_size)
            property_files_tsv = list(temp_dir.glob("**/*.tsv"))
            property_files_csv = list(temp_dir.glob("**/*.csv"))
            property_files = (
                property_files_tsv + property_files_csv
            )  # Combine both types

            if property_files:
                # Load the column mapping from the .pkl file
                with open(pkl_path, "rb") as pkl_file:
                    column_mapping = pickle.load(
                        pkl_file
                    )  # Load the .pkl file into column_mapping

                use_celery = bool(REDIS_URL)  # Use Celery if Redis is configured
                for property_file in property_files:
                    sep = "," if property_file.suffix == ".csv" else "\t"
                    import_property(
                        str(property_file),
                        sep,
                        use_celery,
                        column_mapping,
                        batch_size=batch_size,
                    )  # Pass column_mapping

        else:
            batch_size = SAMPLE_BATCH_SIZE
            print("Batch size:", batch_size)
            # var and vcf
            sample_files = list(temp_dir.joinpath("samples").glob("**/*.sample"))
            anno_files = list(temp_dir.joinpath("anno").glob("**/*.vcf.*"))
            print(f"Sample: {len(sample_files)} files found")
            print(f"Annotation (vcfs): {len(anno_files)} files found")
            if len(sample_files) > 0:
                import_type = ImportLog.ImportType.SAMPLE
            elif len(anno_files) > 0:
                import_type = ImportLog.ImportType.ANNOTATION
            else:
                import_type = ImportLog.ImportType.SAMPLE_ANNOTATION_ARCHIVE

            timer = datetime.now()

            number_of_batches = (
                (len(sample_files) + batch_size - 1) // batch_size
                if sample_files
                else (len(anno_files) + batch_size - 1) // batch_size
            )

            print(f"Total number of batches: {number_of_batches}")
            sample_files = [str(file) for file in sample_files]
            if batch_size:
                replicon_cache = {}
                gene_cache_by_accession = {}
                gene_cache_by_var_pos = {}
                if REDIS_URL:
                    print("setting up sample import celery jobs..")
                    sample_jobs = []
                    for i in range(0, len(sample_files), batch_size):
                        batch = sample_files[i : i + batch_size]
                        sample_jobs.append(
                            process_batch.s(
                                batch,
                                replicon_cache,
                                gene_cache_by_accession,
                                gene_cache_by_var_pos,
                                str(temp_dir),
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
                    replicon_cache = {}
                    gene_cache_by_accession = {}
                    # Samples
                    for i in range(0, len(sample_files), batch_size):
                        # print(
                        #     f"processing batch {(i//batch_size) + 1} of {number_of_batches}"
                        # )
                        # batchtimer = datetime.now()
                        batch = sample_files[i : i + batch_size]
                        process_batch_single_thread(
                            batch,
                            replicon_cache,
                            gene_cache_by_accession,
                            str(temp_dir),
                        )
                    # annotation
                    for file in anno_files:
                        process_annotation(str(file))

                    # print(
                    #     f"batch {(i//batch_size) + 1} done in {datetime.now() - batchtimer}"
                    # )

            LOGGER.info(f"import done in {datetime.now() - timer}")
    except Exception as e:
        # TODO: [optional] if fail, we update the ProcessingJob right now.
        LOGGER.error(f"Error : {e}")
        error_dir = pathlib.Path(SONAR_DATA_ARCHIVE).joinpath("error")
        error_dir.mkdir(parents=True, exist_ok=True)
        process_file_path.rename(error_dir.joinpath(process_file_path.name))
        if pkl_path and pkl_path.exists():
            pkl_path.rename(error_dir.joinpath(pkl_path.name))
        ImportLog.objects.create(
            type=import_type,
            file=FileProcessing.objects.get(file_name=filename_ID),
            success=False,
            exception_text=e,
            stack_trace=traceback.format_exc(),
        )
        LOGGER.error(f"--- Exception: move to {error_dir} ---")

    else:  # no exception occurs
        if KEEP_IMPORTED_DATA_FILES:
            completed_dir = pathlib.Path(SONAR_DATA_ARCHIVE).joinpath("completed")
            completed_dir.mkdir(parents=True, exist_ok=True)
            process_file_path.rename(completed_dir.joinpath(process_file_path.name))
            if pkl_path and pkl_path.exists():
                pkl_path.rename(completed_dir.joinpath(pkl_path.name))
            LOGGER.info(f"--- Finish: move to {completed_dir} ---")
        else:
            # Delete files after import rather than keeping them in the
            # archive/completed/ dir
            process_file_path.unlink()
            if pkl_path and pkl_path.exists():
                pkl_path.unlink()
        ImportLog.objects.create(
            type=import_type,
            file=FileProcessing.objects.get(file_name=filename_ID),
            success=True,
        )
    finally:
        # TODO: need to rethink about how to finalize the job status
        # The  _file_count = total_all_file - total_file is not a great idea
        shutil.rmtree(temp_dir)
        # --- update job status

        # list all related files
        all_file_obj = FileProcessing.objects.filter(processing_job__job_name=job_ID)
        total_all_file = all_file_obj.count()
        all_file_names_list = all_file_obj.values_list("file_name", flat=True)
        # Import search only success and count
        _file_obj = ImportLog.objects.filter(file__in=all_file_names_list)
        total_file = _file_obj.count()
        # Calculate the difference between total files and successful imports
        _file_count = total_all_file - total_file
        # Update ProcessingJob status based on file processing status
        if _file_count > 0:
            # "In Progress"
            ProcessingJob.objects.filter(job_name=job_ID).update(
                status=ProcessingJob.ImportType.IN_PROGRESS
            )
            # print("In progress: %s", _file_count)
        else:
            # If all files are successfully processed, check if any errors occurred during import
            error_files = ImportLog.objects.filter(file__in=all_file_obj, success=False)
            if error_files.exists():
                #  "Failed"
                ProcessingJob.objects.filter(job_name=job_ID).update(
                    status=ProcessingJob.ImportType.FAILED
                )
                # print(f"### Job ID: {job_ID} \nRun status: Failed")
                LOGGER.error(f"### Job ID: {job_ID} \nRun status: Failed")
            else:
                #  "Completed"
                ProcessingJob.objects.filter(job_name=job_ID).update(
                    status=ProcessingJob.ImportType.COMPLETED
                )
                LOGGER.info(f"### Job ID: {job_ID} \nRun status: Completed")


@shared_task
def process_batch(
    batch: list[str],
    replicon_cache,
    gene_cache_by_accession,
    gene_cache_by_var_pos,
    temp_dir,
):
    parameters = locals().copy()
    if PROFILE_IMPORT:
        lp = LineProfiler()
        # Add a few of the slowest functions based on profiling the
        # process_batch_run() function
        lp.add_function(SampleImport.get_mutation_objs)
        lp.add_function(get_mutation2alignment_objs)
        process_batch_profiled = lp(process_batch_run)
        retval = process_batch_profiled(**parameters)
        lp.print_stats()
        return retval
    else:
        return process_batch_run(**parameters)


def process_batch_run(
    batch: list[str],
    replicon_cache,
    gene_cache_by_accession,
    gene_cache_by_var_pos,
    temp_dir,
):
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
                update_fields=["length", "sequence", "last_update_date"],
            )
        [x.update_replicon_obj(replicon_cache) for x in sample_import_objs]
        alignments: list[Alignment] = []
        for sample_import_obj in sample_import_objs:
            sample_import_obj.create_alignment(alignments)
        with cache.lock("alignment"):
            Alignment.objects.bulk_create(
                alignments,
                update_conflicts=True,
                unique_fields=["sequence", "replicon"],
                update_fields=["sequence", "replicon"],
            )

        nt_mutation_set: list[NucleotideMutation] = []
        cds_mutation_set: list[AminoAcidMutation] = []
        mutation_parent_relations = []
        nt_mutation_alignment_relations: list[NucleotideMutation.alignments.through] = (
            []
        )
        aa_mutation_alignment_relations: list[AminoAcidMutation.alignments.through] = []
        for sample_import_obj in sample_import_objs:
            id_to_mutation_mapping = sample_import_obj.get_mutation_objs_nt(
                nt_mutation_set,
                replicon_cache,
                gene_cache_by_var_pos,
                nt_mutation_alignment_relations,
            )
            parent_relations = (
                sample_import_obj.get_mutation_objs_cds_and_parent_relations(
                    cds_mutation_set,
                    gene_cache_by_accession,
                    id_to_mutation_mapping,
                    aa_mutation_alignment_relations,
                )
            )
            mutation_parent_relations.extend(parent_relations)
        with cache.lock("mutation"):
            NucleotideMutation.objects.bulk_create(
                nt_mutation_set,
                update_conflicts=True,
                unique_fields=["ref", "alt", "start", "end", "replicon"],
                update_fields=["ref", "alt", "start", "end", "replicon"],
            )
            AminoAcidMutation.objects.bulk_create(
                cds_mutation_set,
                update_conflicts=True,
                unique_fields=["ref", "alt", "start", "end", "cds"],
                update_fields=["ref", "alt", "start", "end", "cds"],
            )
            AminoAcidMutation.parent.through.objects.bulk_create(
                mutation_parent_relations,
                ignore_conflicts=True,
            )
            NucleotideMutation.alignments.through.objects.bulk_create(
                [
                    NucleotideMutation.alignments.through(
                        nucleotidemutation_id=rel.nucleotidemutation.id,
                        alignment_id=rel.alignment.id,
                    )
                    for rel in nt_mutation_alignment_relations
                ],
                ignore_conflicts=True,
            )
            AminoAcidMutation.alignments.through.objects.bulk_create(
                [
                    AminoAcidMutation.alignments.through(
                        aminoacidmutation_id=rel.aminoacidmutation.id,
                        alignment_id=rel.alignment.id,
                    )
                    for rel in aa_mutation_alignment_relations
                ],
                ignore_conflicts=True,
            )

        return (True, None, None)

    except Exception as e:
        # Handle the DataError exception here
        LOGGER.error(f"DataError: {e}")
        # Perform additional error handling or logging as needed
        LOGGER.error("Error happens on this batch")
        return (False, str(e), traceback.format_exc())


@shared_task
def process_annotation(file_name):
    try:
        annotation_import = AnnotationImport(file_name)
        if REDIS_URL:
            with cache.lock("annotation"):
                AnnotationType.objects.bulk_create(
                    annotation_import.get_annotation_objs(),
                    ignore_conflicts=True,
                )
            with cache.lock("annotation2mutation"):
                AnnotationType.mutations.through.objects.bulk_create(
                    annotation_import.get_annotation2mutation_objs(),
                    ignore_conflicts=True,
                )
        else:
            AnnotationType.objects.bulk_create(
                annotation_import.get_annotation_objs(),
                ignore_conflicts=True,
            )
            AnnotationType.mutations.through.objects.bulk_create(
                annotation_import.get_annotation2mutation_objs(), ignore_conflicts=True
            )
    except Exception as e:
        LOGGER.error(f"Error in process_annotation: {e}")
        return (False, str(e), traceback.format_exc())
    return (True, None, None)


def process_batch_single_thread(
    batch, replicon_cache, gene_cache_by_accession, temp_dir
):
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
                sample_import_obj.create_alignment()
                for sample_import_obj in sample_import_objs
            ]
            Alignment.objects.bulk_create(alignments, ignore_conflicts=True)
            mutations = []
            for sample_import_obj in sample_import_objs:
                mutations.extend(
                    sample_import_obj.get_mutation_objs(gene_cache_by_accession)
                )
            Mutation.objects.bulk_create(mutations, ignore_conflicts=True)
            mutations2alignments = []
            for sample_import_obj in sample_import_objs:
                mutations2alignments.extend(
                    sample_import_obj.get_mutation2alignment_objs()
                )
            Mutation.alignments.through.objects.bulk_create(
                mutations2alignments, ignore_conflicts=True
            )
            # annotations = []
            # for sample_import_obj in sample_import_objs:
            #     annotations.extend(sample_import_obj.get_annotation_objs())
            # AnnotationType.objects.bulk_create(
            #     annotations,
            #     ignore_conflicts=True,
            # )
            # annotation2mutations = []
            # for sample_import_obj in sample_import_objs:
            #     annotation2mutations.extend(
            #         sample_import_obj.get_annotation2mutation_objs()
            #     )
            # Mutation2Annotation.objects.bulk_create(
            #     annotation2mutations, ignore_conflicts=True
            # )

            # Filter sequences without associated samples
            # clean_unused_sequences()

    except DataError as data_error:
        # Handle the DataError exception here
        LOGGER.error(f"DataError: {data_error}")
        # Perform additional error handling or logging as needed
        LOGGER.error("Error happens on this batch")
        for sample_import_obj in sample_import_objs:
            LOGGER.error(f"{sample_import_obj.sample_file_path}")
        raise
    except Exception as e:
        # Handle other exceptions if necessary
        LOGGER.critical(f"An unexpected error occurred: {e}")
        raise


def import_property(
    property_file, sep, use_celery=False, column_mapping=None, batch_size=1000
):

    try:
        # Load the CSV file in batches
        properties_df = pd.read_csv(
            property_file,
            sep=sep,
            dtype="string",
            keep_default_na=False,
            # chunksize=batch_size,
        )

        timer = datetime.now()

        # Use Celery if parallel processing is enabled
        # Convert column_mapping object (PropertyColumnMapping class) to a JSON-serializable format
        # because celery takes JSON-serializable data (like dictionaries or lists) and  passes to the Celery tasks
        if column_mapping is not None:
            serializable_column_mapping = {
                k: {
                    "db_property_name": v.db_property_name,
                    "data_type": v.data_type,
                    "default": v.default,
                }
                for k, v in column_mapping["column_mapping"].items()
            }
            sample_id_column = column_mapping["sample_id_column"]
        else:
            serializable_column_mapping = None
            sample_id_column = "ID"

        # Data preprocessing

        for column_name, col_info in serializable_column_mapping.items():

            if column_name not in properties_df.columns:
                print(
                    f"Skipping column '{column_name}' as it is not in the property file."
                )
                continue
            # Apply default values for missing or empty fields
            default_value = col_info["default"]
            print(f"{column_name} :pairs with: {col_info}")

            if default_value is not None:

                properties_df[column_name] = (
                    properties_df[column_name]
                    .replace("", default_value)  # Replace empty strings
                    .fillna(default_value)  # Replace NaN values
                )

            # # Explicitly convert the column to string to avoid .0 issues
            # if (
            #     col_info["data_type"] == "value_varchar"
            #     and column_name in properties_df.columns
            # ):
            #     properties_df[column_name] = properties_df[column_name].astype(str)

            # Format columns with 'value_date' type
            if (
                col_info["data_type"] == "value_date"
                and column_name in properties_df.columns
            ):
                properties_df[column_name] = properties_df[column_name].apply(
                    parse_date
                )
        if use_celery:
            print("Setting up property import celery jobs...")

            property_jobs = []
            for i in range(0, len(properties_df), batch_size):
                batch = properties_df.iloc[i : i + batch_size]
                batch_as_dict = batch.to_dict(orient="records")
                property_jobs.append(
                    process_property_batch.s(
                        batch_as_dict, sample_id_column, serializable_column_mapping
                    )  # Pass column_mapping
                )

            # Run the Celery group of tasks and collect results
            results = group(property_jobs).apply_async().get()

            for result in results:
                if not result[0]:
                    raise Exception(f"Property Import Error: {result[1]}")

        else:
            print("Processing properties in single-threaded mode...")

            # Process the CSV file in a single-threaded manner
            batch_as_dict = properties_df.to_dict(orient="records")
            # column_mapping does not need to be JSON-serializable format, because we use only single thread
            _process_property_file(
                batch_as_dict, sample_id_column, column_mapping["column_mapping"]
            )

        print(f"Property import usage time: {datetime.now() - timer}")

    except Exception as e:
        print("Error in import_property func.:", e)
        print(f"Error in import_property line#: {e.__traceback__.tb_lineno}")
        raise  # Re-raise the exception to propagate it up the stack?


@shared_task
def process_property_batch(batch_as_dict, sample_id_column, serialized_column_mapping):
    # Reconstruct column_mapping from the serialized format
    if serialized_column_mapping is not None:
        column_mapping = {
            k: PropertyColumnMapping(
                db_property_name=v["db_property_name"],
                data_type=v["data_type"],
                default=v["default"],
            )
            for k, v in serialized_column_mapping.items()
        }
    else:
        column_mapping = None

    try:
        _process_property_file(batch_as_dict, sample_id_column, column_mapping)
    except Exception as e:
        print("Error in process_property_batch func.:", e)
        print(f"Error in process_property_batch line#: {e.__traceback__.tb_lineno}")
        return False, f"Failed or interrupted batch job: {e}"
    return True, "Batch processed successfully"


def _process_property_file(batch_as_dict, sample_id_column, column_mapping):
    """
    Logic for processing a batch of the property file
    """

    properties_df = pd.DataFrame.from_dict(batch_as_dict, dtype=object)
    sample_property_names = []
    custom_property_names = []

    for property_name in properties_df.columns:

        if property_name in column_mapping.keys():
            db_property_name = column_mapping[property_name].db_property_name
            try:
                models.Sample._meta.get_field(db_property_name)
                sample_property_names.append(db_property_name)
            except FieldDoesNotExist:
                custom_property_names.append(property_name)

    sample_id_set = set(properties_df[sample_id_column])
    samples = models.Sample.objects.filter(name__in=sample_id_set).iterator()

    sample_updates = []
    property_updates = []
    properties_df.convert_dtypes()
    properties_df.set_index(sample_id_column, inplace=True)
    try:
        for sample in samples:

            row = properties_df[properties_df.index == sample.name]

            sample.last_update_date = timezone.now()
            for name, value in row.items():
                if name in column_mapping.keys():
                    db_name = column_mapping[name].db_property_name
                    if db_name in sample_property_names:
                        setattr(sample, db_name, value.values[0])
            sample_updates.append(sample)

            # Update custom properties
            property_updates += _create_property_updates(
                sample,
                {
                    column_mapping[name].db_property_name: {
                        "value": (
                            value.values[0]
                            if value.values[0]
                            else column_mapping[name].default
                            # Fallback value if default is also None (NULL in database)
                        ),
                        "datatype": column_mapping[name].data_type,
                    }
                    for name, value in row.items()
                    if name in custom_property_names
                },
                use_property_cache=True,
                property_cache=property_cache,  # global variable
            )
    except Exception as e:
        print(f"Error :{e}")
        print(f"Error processing sample data: {row.to_dict(orient='records')}")
        print(f"error in _process_property_file line#: {e.__traceback__.tb_lineno}")
        raise  # Or raise the exception

    with transaction.atomic():
        # Bulk update samples
        # when there is no update/add to based prop.
        if sample_property_names:
            models.Sample.objects.bulk_update(
                sample_updates, sample_property_names + ["last_update_date"]
            )

        # update custom prop. for Sample
        serializer = Sample2PropertyBulkCreateOrUpdateSerializer(
            data=property_updates, many=True
        )
        serializer.is_valid(raise_exception=True)
        models.Sample2Property.objects.bulk_create(
            [models.Sample2Property(**data) for data in serializer.validated_data],
            update_conflicts=True,
            update_fields=[
                "value_integer",
                "value_float",
                "value_text",
                "value_varchar",
                "value_blob",
                "value_date",
                "value_zip",
            ],
            unique_fields=["sample", "property"],
        )


def _create_property_updates(
    sample, properties: dict, use_property_cache=False, property_cache=None
) -> list[dict]:
    property_objects = []
    if use_property_cache:
        if property_cache is None:
            property_cache = {}
        # Pre-build or refresh cache for all properties
        for name, value in properties.items():
            # if name not in property_cache:
            property_cache[name] = models.Property.objects.get_or_create(
                name=name, datatype=value["datatype"]
            )[0].id

    for name, value in properties.items():
        property = {"sample": sample.id, value["datatype"]: value["value"]}
        if use_property_cache:
            # Use the prebuilt property_cache
            property["property"] = property_cache[name]
        else:
            # Fetch property directly
            property["property"] = models.Property.objects.get_or_create(
                name=name, datatype=value["datatype"]
            )[0].id

        property_objects.append(property)
    return property_objects
