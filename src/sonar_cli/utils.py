import collections
import csv
import datetime
from io import BytesIO
import json
import os
import sys
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
import zipfile

from mpire import WorkerPool
from sonar_cli.align import sonarAligner
from sonar_cli.annotation import Annotator
from sonar_cli.api_interface import APIClient
from sonar_cli.cache import sonarCache
from sonar_cli.config import ANNO_TOOL_PATH
from sonar_cli.config import BASE_URL
from sonar_cli.config import SNPSIFT_TOOL_PATH
from sonar_cli.config import VCF_ONEPERLINE_PATH
from sonar_cli.dbm import sonarDBManager
from sonar_cli.logging import LoggingConfigurator
from sonar_cli.utils_1 import _get_csv_colnames
from sonar_cli.utils_1 import open_file_autodetect
from sonar_cli.utils_1 import out_autodetect
from sonar_cli.utils_1 import read_var_file
from tqdm import tqdm

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()


class sonarUtils:
    """
    A class used to perform operations on a Tool's database.
    """

    def __init__(self):
        pass

    # DATA IMPORT
    @staticmethod
    def import_data(
        # db: str,
        fasta: List[str] = [],
        csv_files: List[str] = [],
        tsv_files: List[str] = [],
        prop_links: List[str] = [],
        cachedir: str = None,
        autolink: bool = False,
        auto_anno: bool = False,
        progress: bool = False,
        update: bool = True,
        threads: int = 1,
        quiet: bool = False,
        reference: str = None,
        method: int = 1,
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

        # checks
        fasta = fasta or []
        tsv_files = tsv_files or []
        csv_files = csv_files or []

        if not _files_exist(*fasta, *tsv_files, *csv_files):
            LOGGER.error("At least one provided file does not exist.")
            sys.exit(1)
        if not _is_import_required(fasta, tsv_files, csv_files, update):
            LOGGER.info("Nothing to import.")
            sys.exit(0)

        sonarUtils._check_reference(reference)

        # property handling
        # NOTE:
        # In the future, we need to edit/design the code to
        # be more flexible when managing newly added properties.
        if prop_links:
            prop_names = sonarUtils._get_prop_names(prop_links, autolink)
            # extract properties form csv/tsv files
            # properties = sonarUtils._extract_props(csv_files, tsv_files, prop_names, quiet)
            sample_id_column = prop_names["sample"]
            properties = {
                "SEQUENCE.DATE_OF_SAMPLING": {
                    "db_property_name": "collection_date",
                    "data_type": "value_varchar",
                },
                "SEQUENCE.SEQUENCING_METHOD": {
                    "db_property_name": "sequencing_tech",
                    "data_type": "value_varchar",
                },
                "DL.POSTAL_CODE": {
                    "db_property_name": "zip_code",
                    "data_type": "value_varchar",
                },
                "SL.ID": {"db_property_name": "lab", "data_type": "value_varchar"},
                "PANGOLIN.LINEAGE_LATEST": {
                    "db_property_name": "lineage",
                    "data_type": "value_varchar",
                },
                "SEQUENCE.SEQUENCING_REASON": {
                    "db_property_name": "sequencing_reason",
                    "data_type": "value_varchar",
                },
                "SEQUENCE.SAMPLE_TYPE": {
                    "db_property_name": "sample_type",
                    "data_type": "value_varchar",
                },
            }
        else:
            # if prop_links is not provide but csv/tsv given....
            if csv_files or tsv_files:
                LOGGER.error(
                    "Cannot link sample name, please add --cols to the command line."
                )
                sys.exit(1)

        # setup cache
        cache = sonarUtils._setup_cache(
            reference=reference, cachedir=cachedir, update=update, progress=progress
        )

        # importing sequences
        if fasta:
            sonarUtils._import_fasta(
                fasta, properties, cache, threads, progress, method, auto_anno
            )

        # TODO: change to API calls
        # importing properties
        if csv_files or tsv_files:
            sonarUtils._import_properties(
                sample_id_column,
                properties,
                csv_files,
                tsv_files,
                progress=progress,
            )

        current_time = datetime.datetime.now().strftime("%d.%b %Y %H:%M:%S")
        LOGGER.info(f"---- Done: {current_time} ----\n")
        cache.logfile_obj.write(f"---- Done: {current_time} ----\n")

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
    ) -> None:
        """
        Process and import sequences from fasta files.

        Args:
            fasta_files: List of paths to fasta files.
            properties: Dictionary of properties linked to sample names.
            cache: Instance of sonarCache.
            threads: Number of threads to use for processing.
            progress: Whether to show progress bar.
            method: Alignment method 1 MAFFT , 2 Parasail
        """
        if not fasta_files:
            return

        cache.add_fasta(*fasta_files, properties=properties, method=method)

        LOGGER.info(f"Total input sample: {len(cache._samplefiles)}")
        # Align sequences and process
        aligner = sonarAligner(cache_outdir=cache.basedir, method=method)
        l = len(cache._samplefiles_to_profile)
        LOGGER.info(f"Total sample needs to be processed: {l}")
        with WorkerPool(n_jobs=threads, start_method="fork") as pool, tqdm(
            desc="profiling sequences...",
            total=l,
            unit="seqs",
            bar_format="{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]",
            disable=not progress,
        ) as pbar:
            for _ in pool.imap_unordered(
                aligner.process_cached_sample, cache._samplefiles_to_profile
            ):
                pbar.update(1)

        passed_samples_list = cache.perform_paranoid_cached_samples()

        if auto_anno:
            # paired_anno_samples_list = [ {'db_path': self.db, 'sample_data': sample} for sample in anno_samples_list]
            with WorkerPool(
                n_jobs=threads, start_method="fork", shared_objects=cache
            ) as pool, tqdm(
                position=0,
                leave=True,
                desc="annotate samples...",
                total=len(passed_samples_list),
                unit="samples",
                bar_format="{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]",
                disable=not progress,
            ) as pbar:
                for _ in pool.imap_unordered(
                    sonarUtils.annotate_sample, passed_samples_list
                ):
                    pbar.update(1)

        # Send Result over network.
        if True:
            with WorkerPool(
                n_jobs=threads, start_method="fork", shared_objects=cache
            ) as pool, tqdm(
                position=0,
                leave=True,
                desc="Sending sample...",
                total=len(passed_samples_list),
                unit="samples",
                bar_format="{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]",
                disable=not progress,
            ) as pbar:
                for _ in pool.imap_unordered(
                    sonarUtils.zip_import_upload, passed_samples_list
                ):
                    pbar.update(1)

        if method == 1:
            # LOGGER.info("Clean uncessary cache")
            cache.clear_unnecessary_cache(passed_samples_list)

    @staticmethod
    def _import_upload(shared_objects, **kwargs):
        """
        (Deplecated)
        No compression is applied,
        """
        cache = shared_objects

        anno_vcf_file = open(kwargs["anno_vcf_file"], "rb")
        var_file = open(kwargs["var_file"], "rb")
        sample_file = open(cache.get_sample_fname(sample_name=kwargs["name"]), "rb")
        files = {
            "anno_file": anno_vcf_file,
            "var_file": var_file,
            "sample_file": sample_file,
        }

        APIClient(base_url=BASE_URL).post_import_upload(files)

    @staticmethod
    def zip_import_upload(shared_objects, **kwargs):
        cache = shared_objects

        anno_vcf_file = kwargs["anno_vcf_file"]
        var_file = kwargs["var_file"]
        sample_file = cache.get_sample_fname(sample_name=kwargs["name"])
        files_to_compress = [anno_vcf_file, var_file, sample_file]

        # Create a zip file without writing to disk
        compressed_data = BytesIO()
        with zipfile.ZipFile(compressed_data, "w", zipfile.ZIP_LZMA) as zipf:
            for file_path in files_to_compress:
                # Get the relative path without the common prefix
                rel_path = os.path.relpath(
                    file_path, os.path.commonprefix(files_to_compress)
                )
                zipf.write(file_path, arcname=rel_path)
        compressed_data.seek(0)
        files = {
            "zip_file": compressed_data,
        }
        APIClient(base_url=BASE_URL).post_import_upload(files)

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

        with sonarDBManager(db, readonly=False) as dbm:
            for sample_name in tqdm(
                properties,
                desc="Import data...",
                total=len(properties),
                unit="samples",
                bar_format="{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]",
                disable=not progress,
            ):
                sample_id = dbm.get_sample_id(sample_name)
                if not sample_id:
                    continue
                for property_name, value in properties[sample_name].items():
                    dbm.insert_property(sample_id, property_name, value)
        """
        LOGGER.info("Import properties")

        all_files = tsv_files + csv_files
        for _file in tqdm(
            all_files,
            desc="Sending property (tsv data)...",
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
            passed, message = APIClient(base_url=BASE_URL).post_import_property_upload(
                data=data, file=file
            )
            if not passed:
                LOGGER.error(message)

        LOGGER.info("Property import completed")

    @staticmethod
    def _get_prop_names(
        # db: str,
        prop_links: List[str],
        autolink: bool,
    ) -> Dict[str, str]:
        """get property names based on user input."""
        # db_properties = sonarUtils._get_properties_from_db(db)
        # propnames = {x: x for x in db_properties} if autolink else {}
        propnames = {}
        for link in prop_links:
            if link.count("=") != 1:
                LOGGER.error(
                    "'" + link + "' is not a valid column-to-property assignment."
                )
                sys.exit(1)
            prop, col = link.split("=")
            if prop == "SAMPLE":
                prop = "sample"

            # if prop not in db_properties:
            #    LOGGER.error(
            #        "Sample property '"
            #        + prop
            #        + "' is unknown to the selected database. Use list-props to see all valid properties."
            #    )
            #    sys.exit(1)
            propnames[prop] = col

        return propnames

    @staticmethod
    def _extract_props(
        csv_files: List[str],
        tsv_files: List[str],
        prop_names: Dict[str, str],
        quiet: bool,
    ) -> Dict:
        """Process the CSV and TSV files."""
        properties = collections.defaultdict(dict)
        # check if necessary
        if not csv_files and not tsv_files:
            return properties

        # process files
        file_tuples = [(x, ",") for x in csv_files] + [(x, "\t") for x in tsv_files]
        for fname, delim in file_tuples:
            if not quiet:
                LOGGER.info("linking data from " + fname + "...")
            col_names = _get_csv_colnames(fname, delim)
            col_to_prop_links = _link_columns_to_props(col_names, prop_names, quiet)
            with open_file_autodetect(fname) as handle:
                csvreader = csv.DictReader(handle, delimiter=delim)
                for row in csvreader:
                    sample = row[col_to_prop_links["sample"]]
                    for x, v in col_to_prop_links.items():
                        if x != "sample":
                            properties[sample][x] = row[v]

        return properties

    @staticmethod
    def _get_properties_from_db(db: str) -> Set[str]:
        """Get the properties stored in the database."""
        with sonarDBManager(db, readonly=True) as dbm:
            db_properties = set(dbm.properties.keys())
        db_properties.add("sample")
        return db_properties

    def _check_reference(reference):
        accession_list = APIClient(base_url=BASE_URL).get_all_reference()
        if reference is not None and reference not in accession_list:
            LOGGER.error(f"The reference {reference} does not exist.")
            sys.exit(1)

    # MATCHING
    @staticmethod
    def match(
        db: str,
        profiles: List[str] = [],
        samples: List[str] = [],
        properties: Dict[str, str] = {},
        reference: Optional[str] = None,
        outfile: Optional[str] = None,
        output_column: Optional[List[str]] = [],
        format: str = "csv",
        showNX: bool = False,
        ignore_terminal_gaps: bool = True,
        frameshifts_only: bool = False,
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
        sonarUtils._check_reference(reference)

        # if not reference:
        #    reference = dbm.get_default_reference_accession()
        #    LOGGER.info(f"Using Default Reference: {reference}")
        rows = APIClient(base_url=BASE_URL).get_variant_profile_bymatch_command(
            profiles=profiles,
            samples=samples,
            reference_accession=reference,
            properties=properties,
            format=format,
            output_columns=output_column,
            filter_n=not showNX,
            filter_x=not showNX,
            frameshifts_only=frameshifts_only,
            ignore_terminal_gaps=ignore_terminal_gaps,
        )

        sonarUtils._export_query_results(
            rows, format, reference, outfile, output_column, db
        )

    @staticmethod
    def annotate_sample(shared_objects, **kwargs):

        """

        kwargs are sample dict object
        """
        cache = shared_objects
        # TODO: check if it is already exist
        # if os.path.exists(kwargs["anno_vcf_file"]):
        #    return
        # export_vcf
        sonarUtils.export_vcf(
            cursor=kwargs,
            cache=cache,
            reference=kwargs["refmol"],
            outfile=kwargs["vcffile"],
            from_var_file=True,
        )

        """
        sonarUtils.match(
            db=db_path,
            reference=sample_data["refmol"],
            samples=[sample_data["name"]],
            outfile=sample_data["vcffile"],
            format="vcf",
        )

        """

        annotator = Annotator(ANNO_TOOL_PATH, SNPSIFT_TOOL_PATH, VCF_ONEPERLINE_PATH)
        annotator.snpeff_annotate(
            kwargs["vcffile"],
            kwargs["anno_vcf_file"],
            kwargs["refmol"],
        )
        # annotator.snpeff_transform_output(
        #    sample_data["anno_vcf_file"], sample_data["anno_tsv_file"]
        # )

        # import annotation
        # import_annvcf_SonarCMD(
        #    db_path,
        #    get_filename_sonarhash(sample_data["vcffile"]),
        #    sample_data["anno_tsv_file"],
        # )

    @staticmethod
    def _export_query_results(
        cursor: object,
        format: str,
        reference: str,
        outfile: Optional[str],
        output_column: Optional[List[str]] = [],
        db: Optional[str] = None,
    ):
        """
        Export results depending on the specified format.

        Args:
            cursor: Cursor object.
            format: Output format.
            reference: Reference accession.
            outfile: Output file path.

        Returns:
            None.
        """
        if format in ["csv", "tsv"]:
            tsv = format == "tsv"
            sonarUtils.export_csv(
                cursor,
                output_column=output_column,
                outfile=outfile,
                na="*** no match ***",
                tsv=tsv,
            )
        elif format == "vcf":
            sonarUtils.export_vcf(
                cursor,
                reference=reference,
                outfile=outfile,
                na="*** no match ***",
                db=db,
            )
        else:
            LOGGER.error(f"'{format}' is not a valid output format")
            sys.exit(1)

    # vcf
    @staticmethod
    def export_vcf(
        cursor,
        reference: str,
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
            _dict = cache.sources[reference]
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


def _get_vcf_data_form_var_file(cursor, selected_ref_seq, showNX) -> Dict:
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


def _write_vcf_records(handle, records: Dict, all_samples: List[str]):
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


def _is_import_required(
    fasta: List[str], tsv_files: List[str], csv_files: List[str], update: bool
) -> bool:
    """Check if import is required."""
    if not fasta:
        if (not tsv_files and not csv_files) or not update:
            return False
    return True


def _log_import_mode(update: bool, quiet: bool):
    """Log the current import mode."""
    if not quiet:
        LOGGER.info(
            "import mode: updating existing samples"
            if update
            else "import mode: skipping existing samples"
        )


def check_file(fname, exit_on_fail=True):
    """
    Check if a given file path exists.

    Args:
        fname (string): The name and path to an existing file.
        exit_on_fail (boolean): Whether to exit the script if the file doesn't exist.
        Default is True.

    Returns:
        True if the file exists, False otherwise.
    """
    if not os.path.isfile(fname):
        if exit_on_fail:
            sys.exit("Error: The file '" + fname + "' does not exist.")
        return False
    return True


def _files_exist(*files: str) -> bool:
    """Check if files exit."""

    for fname in files:
        if not os.path.isfile(fname):
            return False
    return True


def _link_columns_to_props(
    col_names: List[str], prop_names: Dict[str, str], quiet: bool
) -> Dict[str, str]:
    """
    Link property columns to their corresponding database properties.

    Args:
        fields: List of column names in the metadata file.
        prop_names: Dictionary mapping database property names to column names in the metadata file.
        quiet: Boolean indicating whether to suppress print statements.

    Returns:
        Dictionary linking file columns (values) to database properties (keys).
    """
    links = {}
    props = sorted(prop_names.keys())
    for prop in props:
        prop_name = prop_names[prop]
        c = col_names.count(prop_name)
        if c == 1:
            links[prop] = prop_name
        elif c > 1:
            LOGGER.error(f"'{prop_name}' is not a unique column.")
            sys.exit(1)
    if "sample" not in links:
        LOGGER.error("Missing 'sample' column assignment.")
        sys.exit(1)
    elif len(links) == 1:
        LOGGER.error("The meta file does not provide any informative column.")
        sys.exit(1)
    if not quiet:
        for prop in props:
            if prop in links:
                LOGGER.info("  " + prop + " <- " + links[prop])
            else:
                LOGGER.info("  " + prop + " missing")
    return links
