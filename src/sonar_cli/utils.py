import collections
import csv
from io import BytesIO
import json
import os
import pickle
import sys
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
from sonar_cli.basic import _check_reference
from sonar_cli.basic import _is_import_required
from sonar_cli.basic import _log_import_mode
from sonar_cli.basic import construct_query
from sonar_cli.cache import sonarCache
from sonar_cli.common_utils import _files_exist
from sonar_cli.common_utils import _get_csv_colnames
from sonar_cli.common_utils import calculate_time_difference
from sonar_cli.common_utils import clear_unnecessary_cache
from sonar_cli.common_utils import flatten_json_output
from sonar_cli.common_utils import get_current_time
from sonar_cli.common_utils import get_fname
from sonar_cli.common_utils import out_autodetect
from sonar_cli.common_utils import read_var_file
from sonar_cli.config import ANNO_CHUNK_SIZE
from sonar_cli.config import ANNO_CONFIG_FILE
from sonar_cli.config import ANNO_TOOL_PATH
from sonar_cli.config import BASE_URL
from sonar_cli.logging import LoggingConfigurator
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
    def import_data(
        db: str,
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
        _check_reference(db, reference)
        start_import_time = get_current_time()
        # checks
        fasta = fasta or []
        tsv_files = tsv_files or []
        csv_files = csv_files or []

        _files_exist(*fasta, *tsv_files, *csv_files)
        if not _is_import_required(fasta, tsv_files, csv_files, update):
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
            sample_id_column = properties["sample"]
            del properties["sample"]
            if len(properties) == 0:
                LOGGER.warn(
                    "No column in the file is mapped to the corresponding variables in the database."
                )
        else:
            # if prop_links is not provide but csv/tsv given....
            if csv_files or tsv_files:
                LOGGER.error(
                    "Cannot link sample name, please add --cols to the command line."
                )
                sys.exit(1)

        # setup cache
        cache = sonarUtils._setup_cache(
            db=db,
            reference=reference,
            cachedir=cachedir,
            update=update,
            progress=progress,
        )

        # importing sequences
        if fasta:
            sonarUtils._import_fasta(
                fasta,
                properties,
                cache,
                threads,
                progress,
                method,
                auto_anno,
                no_upload_sample,
            )

        # importing properties
        if csv_files or tsv_files:
            sonarUtils._import_properties(
                sample_id_column,
                properties,
                csv_files,
                tsv_files,
                progress=progress,
            )

        end_import_time = get_current_time()
        LOGGER.info(
            f"\nImport Runtime: {calculate_time_difference(start_import_time, end_import_time)}"
        )
        LOGGER.info(f"---- Done: {end_import_time} ----\n")
        cache.logfile_obj.write(
            f"Import Runtime: {calculate_time_difference(start_import_time, end_import_time)}\n"
        )
        cache.logfile_obj.write(f"---- Done: {end_import_time} ----\n")
        cache.logfile_obj.close()
        cache.error_logfile_obj.write(f"---- Done: {end_import_time} ----\n")
        cache.error_logfile_obj.close()

    @staticmethod
    def _setup_cache(
        db: str = None,
        reference: str = None,
        cachedir: Optional[str] = None,
        update: bool = True,
        progress: bool = False,
        debug: bool = False,
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
        )

    @staticmethod
    def _import_fasta(
        fasta_files: List[str],
        properties: Dict,
        cache: sonarCache,
        threads: int = 1,
        progress: bool = False,
        method: int = 1,
        auto_anno: bool = False,
        no_upload_sample: bool = False,
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

        if not fasta_files:
            return
        start_seqcheck_time = get_current_time()
        sample_data_dict_list = cache.add_fasta_v2(*fasta_files, method=method)

        cache.logfile_obj.write(
            f"Sequence check usage time: {calculate_time_difference(start_seqcheck_time, get_current_time())}\n"
        )
        LOGGER.info(f"Total input samples: {cache.sampleinput_total}")

        # Align sequences and process
        aligner = sonarAligner(
            cache_outdir=cache.basedir, method=method, allow_updates=cache.allow_updates
        )
        l = len(cache._samplefiles_to_profile)
        LOGGER.info(f"Total samples that need to be processed: {l}")
        if l == 0:
            return
        start_align_time = get_current_time()
        with WorkerPool(n_jobs=threads, start_method="fork") as pool, tqdm(
            desc="Profiling sequences...",
            total=l,
            unit="seqs",
            bar_format="{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]",
            disable=not progress,
        ) as pbar:
            for _ in pool.imap_unordered(
                aligner.process_cached_sample, sample_data_dict_list
            ):
                pbar.update(1)

        cache.logfile_obj.write(
            f"Seq. alignment usage time: {calculate_time_difference(start_align_time, get_current_time())}\n"
        )

        start_paranoid_time = get_current_time()
        passed_samples_list = cache.perform_paranoid_cached_samples(
            sample_data_dict_list
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
        if auto_anno:
            anno_result_list = []
            start_anno_time = get_current_time()
            with WorkerPool(
                n_jobs=threads,
                start_method="fork",
                shared_objects=cache,
                pass_worker_id=True,
                use_worker_state=False,
            ) as pool:
                pool.set_shared_objects(cache)
                anno_result_list = pool.map_unordered(
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
            cache.logfile_obj.write(
                f"Sample anno usage time: {calculate_time_difference(start_anno_time, get_current_time())}\n"
            )

        else:
            LOGGER.info("Disable annotation step.")

        # Send Result over network.
        if not no_upload_sample:
            start_upload_time = get_current_time()
            # NOTE: reuse the chunk size from anno
            # n = 500

            with WorkerPool(n_jobs=threads, start_method="fork") as pool, tqdm(
                position=0,
                leave=True,
                desc="Sending sample/variant...",
                total=len(passed_samples_chunk_list),
                unit="chunks",
                bar_format=bar_format,
                disable=not progress,
            ) as pbar:

                for _ in pool.imap_unordered(
                    sonarUtils.zip_import_upload_multithread,
                    passed_samples_chunk_list,
                ):
                    pbar.update(1)

            if auto_anno:
                with WorkerPool(
                    n_jobs=threads,
                    start_method="fork",
                    use_worker_state=False,
                ) as pool:
                    pool.map_unordered(
                        sonarUtils.zip_import_upload_annotaion,
                        anno_result_list,
                        progress_bar=True,
                        progress_bar_options={
                            "position": 0,
                            "desc": "Sending annotated variant...",
                            "unit": "chunks",
                            "bar_format": bar_format,
                        },
                    )

            cache.logfile_obj.write(
                f"Sample upload usage time: {calculate_time_difference(start_upload_time, get_current_time())}\n"
            )

        else:
            LOGGER.info("Disable sending samples.")

        clear_unnecessary_cache(passed_samples_list)

    @staticmethod
    def zip_import_upload_annotaion(file_path):
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

        json_response = APIClient(base_url=BASE_URL).post_import_upload(files)
        msg = json_response["detail"]
        if msg != "File uploaded successfully":
            LOGGER.error(msg)

    @staticmethod
    def zip_import_upload_multithread(*sample_list):

        files_to_compress = []
        for kwargs in sample_list:
            var_file = kwargs["var_file"]
            sample_dict = kwargs

            # Serialize the sample dictionary to bytes
            sample_bytes = pickle.dumps(sample_dict)

            # Append the serialized sample dictionary to the files to compress
            files_to_compress.append(
                (
                    f"samples/{get_fname(kwargs['name'], extension='.sample',enable_parent_dir=True)}",
                    sample_bytes,
                )
            )
            files_to_compress.append(var_file)

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

        json_response = APIClient(base_url=BASE_URL).post_import_upload(files)
        msg = json_response["detail"]
        if msg != "File uploaded successfully":
            LOGGER.error(msg)

    @staticmethod
    def _import_properties(
        sample_id_column: str,
        properties: Dict[str, Dict[str, str]],
        # db: str,
        csv_files: str,
        tsv_files: str,
        progress: bool,
    ):
        """
        Imports properties to the database.

        Args:
            properties: A dictionary of properties, where the key is a sample name and
                        the value is another dictionary of properties for that sample.
            db: The database where the properties will be imported.
            progress: If True, displays a progress bar.

        """
        LOGGER.info("Send property")

        all_files = tsv_files + csv_files
        for _file in tqdm(
            all_files,
            desc="Sending property...",
            total=len(all_files),
            unit="files",
            bar_format="{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]",
            disable=not progress,
        ):
            if _file in tsv_files:
                file_key = "properties_tsv"
            elif _file in csv_files:
                file_key = "properties_csv"

            file = {file_key: open(_file, "rb")}
            data = {
                "sample_id_column": sample_id_column,
                "column_mapping": json.dumps(properties),
            }
            json_response = APIClient(base_url=BASE_URL).post_import_property_upload(
                data=data, file=file
            )
            msg = json_response["detail"]
            if msg != "File uploaded successfully":
                LOGGER.error(msg)

        LOGGER.info("Sending Complete")

    @staticmethod
    def _get_prop_names(  # noqa: C901
        prop_links: List[str],
        autolink: bool,
        csv_files: List[str],
        tsv_files: List[str],
    ) -> Dict[str, str]:
        """
        get property names based on user input.

        "--auto-link" will link columns in the file to existing properties
        in the database (no new property name will be created in database).
        However, if the properties that the user manually inputs don't exist,
        we add those as new properties to the database.

        """
        propnames = {}

        listofkeys, values_listofdict = sonarUtils.get_all_properties()
        prop_df = pd.DataFrame(values_listofdict, columns=listofkeys)
        # print(prop_df)
        # propnames = {x: x for x in prop_df} if autolink else {}
        # print(propnames)

        # link from user input
        for link in prop_links:
            if link.count("=") != 1:
                LOGGER.error(
                    "'" + link + "' is not a valid column-to-property assignment."
                )
                sys.exit(1)
            prop, col = link.split("=")
            #
            if prop.upper() == "SAMPLE":
                prop = "sample"
                propnames[prop] = col
                continue
            # if prop not in db_properties:
            #    LOGGER.error(
            #        "Sample property '"
            #        + prop
            #        + "' is unknown to the selected database. Use list-props to see all valid properties."
            #    )
            #    sys.exit(1)

            # lookup
            # _row_df = prop_df.loc[prop_df["name"] == prop]
            _row_df = prop_df[
                prop_df["name"].str.contains(prop, na=False, case=False, regex=False)
            ]

            if not _row_df.empty:
                query_type = _row_df["query_type"].values[0]
                propnames[col] = {"db_property_name": prop, "data_type": query_type}

        #  link from files, process files- get headers
        if autolink:
            file_tuples = [(x, ",") for x in csv_files] + [(x, "\t") for x in tsv_files]
            col_names_fromfile = []
            for fname, delim in file_tuples:
                # LOGGER.info("linking data from " + fname + "...")
                col_names_fromfile.extend(_get_csv_colnames(fname, delim))

            # NOTE: case insensitive (SAMPLE_TYPE = sample_type)
            col_names_fromfile = list(set(col_names_fromfile))
            for col_name in col_names_fromfile:
                _row_df = prop_df[
                    prop_df["name"].str.contains(
                        col_name, na=False, case=False, regex=False
                    )
                ]

                # prop_df.loc[prop_df["name"] == col_name]
                if not _row_df.empty:
                    query_type = _row_df["query_type"].values[0]
                    name = _row_df["name"].values[0]
                    propnames[col_name] = {
                        "db_property_name": name,
                        "data_type": query_type,
                    }
        # print(propnames)
        LOGGER.info("column corresponds to a property field in database")
        for prop, prop_info in propnames.items():
            if prop == "sample":
                continue
            db_property_name = prop_info.get("db_property_name", "N/A")
            LOGGER.verbose(f"{prop} <- {db_property_name}")

        return propnames

    @staticmethod
    def annotate_sample(
        worker_id, shared_objects: sonarCache, *sample_list
    ):  # **kwargs):
        """

        kwargs are sample dict object
        """

        cache = shared_objects
        refmol = cache.default_refmol_acc
        input_vcf_list = []
        # map_name_annovcf_dict = {}
        _unique_name = ""

        # export_vcf:
        for kwargs in sample_list:
            _unique_name = _unique_name + kwargs["name"]
            input_vcf_list.append(kwargs["vcffile"])
            if cache.allow_updates is False:
                if os.path.exists(kwargs["vcffile"]):
                    continue

            sonarUtils.export_vcf(
                cursor=kwargs,
                cache=cache,
                reference=kwargs["refmol"],
                outfile=kwargs["vcffile"],
                from_var_file=True,
            )
            # for split vcf
            # map_name_annovcf_dict[kwargs["name"]] = kwargs["anno_vcf_file"]

        annotator = Annotator(
            annotator_exe_path=ANNO_TOOL_PATH, config_path=ANNO_CONFIG_FILE, cache=cache
        )
        merged_vcf = os.path.join(
            cache.anno_dir, get_fname(_unique_name, extension=".vcf")
        )
        merged_anno_vcf = os.path.join(
            cache.anno_dir, get_fname(_unique_name, extension=".anno.vcf")
        )
        filtered_vcf = os.path.join(
            cache.anno_dir, get_fname(_unique_name, extension=".filtered.anno.vcf")
        )
        if cache.allow_updates is False:
            if os.path.exists(filtered_vcf):
                return filtered_vcf
        # merge vcf:
        if len(input_vcf_list) == 1:
            merged_vcf = input_vcf_list[0]
        else:
            annotator.bcftools_merge(input_vcfs=input_vcf_list, output_vcf=merged_vcf)

        # #  check if it is already exist
        # # NOTE WARN: this doesnt check if the file is corrupt or not, or completed information in the vcf file.
        # if cache.allow_updates is False:
        #     if os.path.exists(kwargs["anno_vcf_file"]):
        #         return

        annotator.snpeff_annotate(
            merged_vcf,
            merged_anno_vcf,
            refmol,
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
        return filtered_vcf

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
        _check_reference(db, reference)

        # if not reference:
        #    reference = dbm.get_default_reference_accession()
        #    LOGGER.info(f"Using Default Reference: {reference}")

        params = {}
        params[
            "filters"
        ] = '{"andFilter":[{"label":"Property","property_name":"sequencing_reason","filter_type":"exact","value":"N"}],"orFilter":[]}'

        params["filters"] = json.dumps(
            construct_query(
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
        params[
            "limit"
        ] = 999999999999999999  # hack (to get all result by using max bigint)
        params["offset"] = 0

        LOGGER.debug(params["filters"])

        json_response = APIClient(
            base_url=BASE_URL
        ).get_variant_profile_bymatch_command(params=params)

        if "results" in json_response:
            rows = json_response
        else:
            LOGGER.error("server cannot return a result")
            sys.exit(1)  # or just return??

        sonarUtils._export_query_results(
            rows,
            format,
            reference,
            outfile=outfile,
            exclude_annotation=exclude_annotation,
            output_column=output_column,
        )

    @staticmethod
    def _export_query_results(
        cursor: object,
        format: str,
        reference: str,
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
        output_column: Optional[List[str]] = [],
        outfile: Optional[str] = None,
        na: str = "*** no data ***",
        tsv: bool = False,
    ) -> None:
        """
        Export the results of a SQL query or a list of rows into a CSV file.

        Parameters:
        data: An iterator over the rows of the query result, or a list of rows.
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
            # get only selected columns
            if output_column:
                first_row = {k: first_row[k] for k in output_column}
        except StopIteration:
            print(na)
            return

        with out_autodetect(outfile) as handle:
            sep = "\t" if tsv else ","
            writer = csv.DictWriter(
                handle,
                fieldnames=first_row.keys(),
                delimiter=sep,
                lineterminator=os.linesep,
            )
            writer.writeheader()
            writer.writerow(first_row)

            for row in data_iter:
                if output_column:
                    row = {k: row[k] for k in output_column}
                writer.writerow(row)

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
            eles if from_var_file is True


        reference: The reference genome name.
        outfile: The output file name. If None, output is printed to stdout.
        na: The string to print if there are no records.
        """
        if not cursor:
            print(na)
        else:
            # TODO: if we want to connect this function with match function
            # we have to put the condition to check the cursor type first.
            _dict = cache.refmols[reference]
            refernce_sequence = _dict["sequence"]

            if from_var_file:
                records, all_samples = _get_vcf_data_form_var_file(
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
            return {"accession": "", "description": "", "organism": ""}
        # only neccessary column
        modified_data = [
            {
                "accession": entry["accession"],
                "description": entry["description"],
                "organism": entry["organism"],
            }
            for entry in rows
        ]

        return modified_data

    @staticmethod
    def add_ref_by_genebank_file(reference_gb, debug=False, default_reference=False):
        """
        add reference
        """
        if default_reference:
            reference_gb = sonarUtils.get_default_reference_gb()
        _files_exist(reference_gb)
        reference_gb_obj = open(reference_gb, "rb")
        try:
            flag = APIClient(base_url=BASE_URL).post_add_reference(reference_gb_obj)

            if flag:
                LOGGER.info("The reference has been added successfully.")
            else:
                LOGGER.error("The reference failed to be added.")
        except Exception as e:
            LOGGER.exception(e)
            LOGGER.error("Fail to process GeneBank file")
            raise

    @staticmethod
    def delete_reference(reference, debug):
        LOGGER.info("Start to delete....the process is not reversible.")

        # delete only reference will also delete the whole linked data.
        """
        if samples_ids:
            if debug:
                logging.info(f"Delete: {samples_ids}")
            for sample in samples_ids:
                # dbm.delete_seqhash(sample["seqhash"])
                dbm.delete_alignment(
                    seqhash=sample["seqhash"], element_id=_ref_element_id
                )
        """
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
        standard: Optional[str] = None,
        check_name: bool = True,
    ) -> int:
        data = {
            "name": name,
            "datatype": datatype,
            "querytype": querytype,
            "description": description,
        }
        json_response = APIClient(base_url=BASE_URL).post_add_property(data)
        LOGGER.info(json_response["detail"])

    @staticmethod
    def delete_property(
        name: str,
    ) -> int:
        json_response = APIClient(base_url=BASE_URL).post_delete_property(name)
        LOGGER.info(json_response["detail"])


def _get_vcf_data_form_var_file(cursor: dict, selected_ref_seq, showNX) -> Dict:
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

    rows = read_var_file(cursor["var_file"], exclude_var_type="cds", showNX=showNX)
    sample_name = cursor["name"]

    for row in rows:
        try:
            if row["variant.start"] - 1 <= 0:
                pre_ref = ""
            else:
                pre_ref = selected_ref_seq[row["variant.start"] - 1]
        except Exception as e:
            LOGGER.error(e)
            raise

        # Split out the data from each row
        chrom, pos, pre_ref, ref, alt, samples = (
            row["variant.reference"],
            row["variant.start"],
            pre_ref,
            row["variant.ref"],
            row["variant.alt"],
            sample_name,
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
            row["variant.start"],
            row["variant.pre_ref"],
            row["variant.ref"],
            row["variant.alt"],
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
    handle.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype"\n')
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
