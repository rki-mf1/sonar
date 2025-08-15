from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
import glob
import hashlib
from itertools import zip_longest
import os
from queue import Queue
import re
import shutil
import subprocess
import sys
import threading
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
from sonar_cli.api_interface import APIClient
from sonar_cli.common_utils import file_collision
from sonar_cli.common_utils import get_fname
from sonar_cli.common_utils import harmonize_seq
from sonar_cli.common_utils import hash_seq
from sonar_cli.common_utils import open_file_autodetect
from sonar_cli.common_utils import remove_charfromsequence_data
from sonar_cli.common_utils import slugify
from sonar_cli.config import BASE_URL
from sonar_cli.config import KSIZE
from sonar_cli.config import SCALED
from sonar_cli.config import TMP_CACHE
from sonar_cli.logging import LoggingConfigurator
from sonar_cli.nextclade_ext import process_single_sample
from sonar_cli.nextclade_ext import read_nextclade_json_streaming
from sonar_cli.sourmash_ext import create_cluster_db
from tqdm import tqdm

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()


def process_paranoid_batch_worker(cache_instance_data, *batch_data):  # noqa: C901
    """
    Standalone worker function for paranoid batch processing using mpire.
    This function processes a batch of samples for paranoid testing.

    Args:
        batch_data: Tuple containing (sample_batch, error_dir)
        cache_instance_data: Dictionary containing necessary data from cache instance

    Returns:
        Tuple of (batch_passed_samples, batch_fail_samples)
    """

    # Initialize logger for this worker
    worker_logger = LoggingConfigurator.get_logger()

    sample_batch, error_dir = batch_data
    batch_fail_samples = []
    batch_passed_samples = []

    worker_logger.debug(
        f"Worker started paranoid check for batch of size {len(sample_batch)}"
    )

    for sample_data in sample_batch:
        try:
            iter_dna_list = []
            # NOTE: right now, we no longer need var_file.
            if "var_file" in sample_data:
                del sample_data["var_file"]
            if "lift_file" in sample_data:
                del sample_data["lift_file"]

            if sample_data["var_parquet_file"] is not None:
                # SECTION:ReadVar
                var_df = pd.read_parquet(sample_data["var_parquet_file"])
                # Currently var_df might be empty if the imported sequence
                # is identical to the reference
                if not var_df.empty:
                    nt_df = var_df[(var_df["type"] == "nt")]
                    iter_dna_list = nt_df[["ref", "alt", "start", "end"]].to_dict(
                        "records"
                    )
                else:
                    worker_logger.warning(
                        f"Paranoid test: var file ({sample_data['var_parquet_file']}) is missing for sample {sample_data['name']}"
                    )

                # SECTION: Paranoid
                if sample_data["seqhash"] is not None:
                    # Get Reference sequence from cache_instance_data
                    ref_sequence = cache_instance_data["refmols"][
                        sample_data["source_acc"]
                    ]["sequence"]
                    seq = list(ref_sequence)

                    prefix = ""
                    gaps = {".", " "}
                    sample_name = sample_data["name"]

                    for vardata in iter_dna_list:
                        if vardata["alt"] in gaps:
                            for i in range(vardata["start"], vardata["end"]):
                                seq[i] = ""
                        elif vardata["alt"] == ".":
                            for i in range(vardata["start"], vardata["end"]):
                                seq[i] = ""
                        elif vardata["start"] >= 0:
                            seq[vardata["start"]] = vardata["alt"]
                        else:
                            prefix = vardata["alt"]

                    # seq is now a restored version from variant dict.
                    seq = prefix + "".join(seq)
                    with open(sample_data["seq_file"], "r") as handle:
                        orig_seq = handle.read()

                    seq = ">" + sample_data["seqhash"] + "\n" + seq + "\n"

                    if seq != orig_seq:
                        worker_logger.warning(
                            f"Failed paranoid test for sample '{sample_name}'"
                        )

                        # Only for printing the sequences with some indication
                        # of mismatches between the original and target sequence
                        min_len = min(len(orig_seq), len(seq))
                        mismatches = []
                        for a, b in zip(list(orig_seq[:min_len]), list(seq[:min_len])):
                            mismatches.append("|" if a == b else "X")
                        worker_logger.debug(f"Original: {orig_seq}")
                        worker_logger.debug(f"        : {''.join(mismatches)}")
                        worker_logger.debug(f"Rebuilt : {seq}")

                        # NOTE: comment this part, for now, we need to discuss which
                        # information we want to report for the failed sample.
                        with open(
                            os.path.join(error_dir, f"{sample_name}.error.var"),
                            "w+",
                        ) as handle:
                            for vardata in iter_dna_list:
                                handle.write(str(vardata) + "\n")

                        qryfile = os.path.join(
                            error_dir,
                            sample_name + ".error.restored_sample.fa",
                        )
                        reffile = os.path.join(
                            error_dir,
                            sample_name + ".error.original_sample.fa",
                        )

                        # NOTE: comment this part, for now, we need to discuss which
                        # information we want to report for the failed sample.
                        with open(qryfile, "w+") as handle:
                            handle.write(seq)
                        with open(reffile, "w+") as handle:
                            handle.write(orig_seq)

                        paranoid_dict = {
                            "sample_name": sample_name,
                        }
                        batch_fail_samples.append(paranoid_dict)
                    else:
                        batch_passed_samples.append(sample_data)

        except Exception as e:
            worker_logger.error(
                f"Error processing sample {sample_data.get('name', 'unknown')}: {str(e)}"
            )
            continue

    return batch_passed_samples, batch_fail_samples


# not sure we need a class for sample or not


class sonarCache:
    def __init__(
        self,
        db: Optional[str] = None,
        outdir: Optional[str] = None,
        refacc: Optional[str] = None,
        logfile: Optional[str] = None,
        allow_updates: bool = False,
        ignore_errors: bool = False,
        temp: bool = False,
        debug: bool = False,
        disable_progress: bool = False,
        include_nx: bool = True,
        auto_anno: bool = False,
    ):
        """
        Initialize the sonarCache object.

        Args:
            db (str): The database to import.
            outdir (str): The output directory to cache data.
            refacc (str): The reference accession.
            logfile (str): The log file to be used.
            allow_updates (bool): Whether to allow updates or not.
            ignore_errors (bool): Whether to skip import errors and keep on going.
            temp (bool): Whether to set cache dir temporary or not.
            disable_progress (bool): Whether to disable progress display or not.
        """
        self.result_queue = Queue()
        self.base_url = db if db else BASE_URL
        self.allow_updates = allow_updates
        self.debug = debug
        self.refacc = refacc
        self.temp = temp
        self.ignore_errors = ignore_errors
        self.disable_progress = disable_progress
        # Molecule/replicon data that belongs to the reference.\
        # self.source replaced by self.refmols
        self.refmols = APIClient(base_url=BASE_URL).get_molecule_data(
            reference_accession=self.refacc,
        )
        if not self.refmols:
            LOGGER.info(f"Cannot find reference: {self.refacc}")
            sys.exit()
        self.default_refmol_acc = [x for x in self.refmols][0]
        self._molregex = re.compile(r"\[molecule=([^\[\]=]+)\]")

        self.basedir = TMP_CACHE if not outdir else os.path.abspath(outdir)
        if self.temp:
            LOGGER.warning(
                f"A cache directory has not been provided. \n The temporary cache is located {self.basedir}. \n Please note that the cache directory is deleted upon successful import."
            )

        if not os.path.exists(self.basedir):
            os.makedirs(self.basedir, exist_ok=True)

        # self.sample_dir = os.path.join(self.basedir, "samples")
        self.seq_dir = os.path.join(self.basedir, "seq")
        self.algn_dir = os.path.join(self.basedir, "algn")
        self.var_dir = os.path.join(self.basedir, "var")
        self.ref_dir = os.path.join(self.basedir, "ref")
        self.error_dir = os.path.join(self.basedir, "error")
        self.anno_dir = os.path.join(self.basedir, "anno")
        self.snpeff_data_dir = os.path.join(self.basedir, "snpeff_data")
        self.blast_dir = os.path.join(self.basedir, "blast")

        os.makedirs(self.snpeff_data_dir, exist_ok=True)
        os.makedirs(self.seq_dir, exist_ok=True)
        os.makedirs(self.ref_dir, exist_ok=True)
        # os.makedirs(self.algn_dir, exist_ok=True)
        os.makedirs(self.var_dir, exist_ok=True)
        # os.makedirs(self.sample_dir, exist_ok=True)
        os.makedirs(self.error_dir, exist_ok=True)
        os.makedirs(self.anno_dir, exist_ok=True)

        self._samplefiles = set()
        self.sampleinput_total = 0
        self._samplefiles_to_profile = 0
        self._samples_dict = dict()

        self._refs = set()
        self._lifts = {}
        self._cds = set()
        self._tt = set()

        self.logfile_name = os.path.join(self.basedir, logfile)
        self.error_logfile_name = os.path.join(self.basedir, "error." + logfile)

        if not os.path.exists(self.logfile_name):
            self.logfile_obj = open(self.logfile_name, "w")
        else:
            self.logfile_obj = open(self.logfile_name, "a+") if logfile else None

        if not os.path.exists(self.error_logfile_name):
            self.error_logfile_obj = open(self.error_logfile_name, "w")
        else:
            self.error_logfile_obj = (
                open(self.error_logfile_name, "a+") if logfile else None
            )
        self.include_nx = include_nx
        self.auto_anno = auto_anno
        if self.auto_anno:
            self.isBuilt_snpEffcache = self.build_snpeff_cache(reference=self.refacc)

            if not self.isBuilt_snpEffcache:
                LOGGER.error(
                    "Could not retrieve the snpEff reference annotation from the sonar server. Aborting."
                )
                sys.exit(1)

        # for segment genome
        self.cluster_db = None
        self.is_segment_import = False
        if len(self.refmols) > 1:
            self.is_segment_import = True
            LOGGER.info(
                "Segment genome detected: creating a database for assigning appropriate reference accession"
            )
            # BUILD BLAST DATABSE
            os.makedirs(self.blast_dir, exist_ok=True)
            self.cluster_db = os.path.join(self.blast_dir, get_fname(self.refacc))
            create_cluster_db(self.refmols, self.cluster_db, KSIZE, SCALED)
            self.blast_best_aln = (
                dict()
            )  # <-- example { fname: {'LC638384.1' (sampleID):'NC_026435.1' (repliconID) , 'LC778458.1':....} (dict) }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if os.path.isdir(self.basedir) and self.temp:
            shutil.rmtree(self.basedir)
        if self.logfile_obj:
            self.logfile_obj.close()

    def add_nextclade_json(  # noqa: C901
        self, *fnames, data_dict_list, chunk_size=100, max_workers=8
    ):
        """

        For each sample, extract the sequence name to construct a data dictionary similar to cache_sample.
        However, we do not need to create it exactly like cache_sample because some variables are unnecessary.

        These are the variables that we need to create :
        name, refmol refmolid refseq_id source_acc sourceid translationid
        algnid header sample_sequence_length nextclade_json_file, vcffile,  anno_vcf_file
        ref_file var_parquet_file var_file include_nx

        """
        # Create lookup dictionary
        sample_lookup_dict = {
            sample_info["name"]: sample_info for sample_info in data_dict_list
        }
        refmol_acc = self.refacc
        sample_data: List[Dict[str, Union[str, int]]] = []

        # Make API call with the batch_data
        api_client = APIClient(base_url=self.base_url)

        if self.is_segment_import:
            gene_rows = api_client.get_elements(molecule_acc=refmol_acc)
        else:
            gene_rows = api_client.get_elements(ref_acc=refmol_acc)

        # Construct a dictionary from gene_rows
        gene_cds_lookup = {}

        for row in gene_rows:
            gene_symbol = row.get("gene.gene_symbol")
            replicon_acc = row.get("replicon.accession")
            cds_list = row.get("cds_list", [])

            for cds in cds_list:
                cds_accession = cds.get("cds.accession")
                if gene_symbol and replicon_acc and cds_accession:
                    gene_cds_lookup[(gene_symbol, replicon_acc)] = cds_accession

        # Process data in chunks
        def process_sample_batch(sample_batch, sample_lookup_dict):
            """Process a batch of samples with their corresponding lookup data"""
            batch_results = []

            for sample_data_dict in sample_batch:
                seqName = sample_data_dict["seqId"]
                # Skip if sample not found in lookup
                if seqName not in sample_lookup_dict:
                    self.error_logfile_obj.write(
                        f"Warning: Sample {seqName} not found in fasta, skipping\n"
                    )
                    continue
                data = sample_lookup_dict[seqName]
                try:
                    # Process the sample
                    process_single_sample(
                        sample_data_dict,
                        refmol_acc,
                        gene_to_cds=gene_cds_lookup,
                        reference_seq=self.refmols[refmol_acc]["sequence"],
                        output_file=data["var_file"],
                        output_parquet_file=data["var_parquet_file"],
                        debug=self.debug,
                    )

                    del data["var_file"]

                    batch_results.append(data)

                except Exception as e:
                    LOGGER.error(f"Error processing sample {seqName}: {str(e)}")
                    self.error_logfile_obj.write(
                        f"Error processing sample {seqName}: {str(e)}\n"
                    )
                    continue

            return batch_results

        # Process each file in streaming fashion
        for fname in fnames:
            print(f"Processing file: {fname}")

            # Stream through the JSON file in chunks
            for file_chunk in read_nextclade_json_streaming(fname, chunk_size):
                if not file_chunk:
                    continue

                seq_names_in_chunk = [sample["seqId"] for sample in file_chunk]
                # print(seq_names_in_chunk)
                # Create filtered sample data dict containing only samples in this chunk
                filtered_sample_data = {
                    seq_name: sample_lookup_dict[seq_name]
                    for seq_name in seq_names_in_chunk
                    if seq_name in sample_lookup_dict
                }
                try:
                    # Split chunk into smaller batches for parallel processing
                    batch_size = min(
                        chunk_size // max_workers, 100
                    )  # Smaller batches for parallel processing
                    batches = [
                        file_chunk[i : i + batch_size]
                        for i in range(0, len(file_chunk), batch_size)
                    ]

                    # Process batches in parallel
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_batch = {
                            executor.submit(
                                process_sample_batch, batch, filtered_sample_data
                            ): batch
                            for batch in batches
                        }

                        # Collect results
                        for future in as_completed(future_to_batch):
                            try:
                                batch_results = future.result()
                                sample_data.extend(batch_results)
                            except Exception as e:
                                LOGGER.error(f"Error processing batch: {str(e)}")
                                self.error_logfile_obj.write(
                                    f"Error processing batch: {str(e)}\n"
                                )
                                continue

                except Exception as e:
                    LOGGER.error(f"Error processing chunk from {fname}: {str(e)}")
                    self.error_logfile_obj.write(
                        f"Error processing chunk from {fname}: {str(e)}\n"
                    )
                    continue
        return sample_data

    def add_fasta_v2(
        self, *fnames, method=1, chunk_size=1000, max_workers=8
    ):  # noqa: C901
        """ """
        sample_data: List[Dict[str, Union[str, int]]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for fname in fnames:
                batch_data = []
                for data in self.iter_fasta(fname):
                    batch_data.append(data)
                    if len(batch_data) == chunk_size:
                        executor.submit(self.process_data_batch, batch_data)
                        batch_data = []
                # Process any remaining data in the last batch
                if batch_data:
                    executor.submit(self.process_data_batch, batch_data)
            # Block until all tasks are done
            executor.shutdown(wait=True)

        # merge all queue results
        while not self.result_queue.empty():
            sample_data.extend(self.result_queue.get())

        return sample_data

    def process_data_batch(
        self,
        batch_data: List[Dict[str, Union[str, int]]],
    ):
        current_thread = threading.current_thread()
        LOGGER.debug(
            f"Thread {current_thread.name} started processing batch of size {len(batch_data)} "
        )
        # Make API call with the batch_data
        api_client = APIClient(base_url=self.base_url)

        # fecth sample_hash
        json_response = api_client.get_bulk_sample_data(
            [data["name"] for data in batch_data]
        )
        sample_dict = {
            sample_info["name"]: {
                "sample_id": sample_info["sample_id"],
                "sequence_seqhash": sample_info["sequence__seqhash"],
            }
            for sample_info in json_response
        }

        # fecth Alignment
        # NOTE: need to evaluate this stmt id more.
        # we assume refmolid == replicon_id == sourceid
        json_response = api_client.get_bulk_alignment_data(
            [
                {"seqhash": data["seqhash"], "replicon_id": data["refmolid"]}
                for data in batch_data
            ]
        )
        alignemnt_dict = {
            data["sequence__sample__name"]: data["alignement_id"]
            for data in json_response
        }

        for i, data in enumerate(batch_data):
            # get sample
            batch_data[i]["sampleid"], seqhash_from_DB = (
                sample_dict[data["name"]]["sample_id"],
                sample_dict[data["name"]]["sequence_seqhash"],
            )

            # reuse the ref mols
            # no dynamic seach or looping search is applied (use the default ref accession number)
            batch_data[i]["sourceid"] = data[
                "refmolid"
            ]  # if self.refmols[self.default_refmol_acc]["id"]== data["refmolid"] else None
            batch_data[i]["source_acc"] = (
                self.refmols[self.default_refmol_acc]["accession"]
                if self.refmols[self.default_refmol_acc]["id"] == data["refmolid"]
                else data["refmol"]
            )
            refseq_accession = data["refmol"]
            batch_data[i]["refseq_id"] = self.get_refseq_id(refseq_accession)

            # Check Alignment if it exists or not (sample and seqhash)
            batch_data[i]["algnid"] = alignemnt_dict.get(data["name"], None)

            batch_data[i]["include_nx"] = self.include_nx

            # Create  path for cache file (e.g., .seq, .ref) and write them.
            # Data variable already point to the original batch_data[i], which if we update
            # the varaible, they altomatically update the original batch_data[i]
            self.add_data_files(data, seqhash_from_DB, refseq_accession)

            # TODO: will exam how to work directly in memory
            # del batch_data[i]["sequence"]
            # reformat data and only neccessay keys are kept.
            _return_data = self.cache_sample(**batch_data[i])
            batch_data[i] = _return_data

        # Note: remove batch_data[i] with empty dict
        batch_data = list(filter(None, batch_data))
        # add result to queue
        self.result_queue.put(batch_data)
        # return batch_data

    def cache_sample(
        self,
        name,
        sampleid,
        seqhash,
        sequence,
        header,
        refmol,
        refmolid,
        refseq_id: int,
        source_acc,
        sourceid,
        translation_id,
        algnid,
        seqfile,
        vcffile,
        anno_vcf_file,
        reffile,
        varparquetfile,
        varfile,
        liftfile: pd.DataFrame,
        cdsfile,
        properties,
        include_nx,
    ):
        """
        The function takes in a bunch of arguments and returns a filename.
        :return: A list of dictionaries. Each dictionary contains the information for a single sample.
        """

        data = {
            "name": name,
            "sampleid": sampleid,
            "refmol": refmol,  # from molecule (replicon)table, moleculd accession <-- we dont use this key at backend
            "refmolid": refmolid,  # from molecule table, moleculd id <-- we dont use this key at backend
            "refseq_id": refseq_id,  # The reference sequence ID. <-- we dont use this key at backend
            "source_acc": source_acc,  # replicon acc
            "sourceid": sourceid,  # replicon id
            "translationid": translation_id,
            "algnid": algnid,
            "header": header,
            "seqhash": seqhash,
            "sample_sequence_length": len(sequence),
            # "sample_sequence": sequence,
            "seq_file": seqfile,
            "vcffile": vcffile,
            "anno_vcf_file": anno_vcf_file,
            "ref_file": reffile,
            "var_parquet_file": varparquetfile,
            "var_file": varfile,
            "lift_file": liftfile,
            "cds_file": cdsfile,
            "properties": properties,
            "include_nx": include_nx,
        }
        # fname = name  # self.get_sample_fname(name)  # return fname with full path
        self.sampleinput_total = self.sampleinput_total + 1
        # NOTE: write files only need to be processed
        if self.allow_updates or algnid is None:
            # try:
            #     self.write_pickle(fname, data)
            # except OSError:
            #     os.makedirs(os.path.dirname(fname), exist_ok=True)
            #     self.write_pickle(fname, data)
            self._samplefiles_to_profile += 1
            # NOTE: IF previous_seqhash != current_seqhash, we have realign and update the variant?
            # uncomment below to enable this
            return data
        elif seqhash is not None:  # changes in seq content
            self._samplefiles_to_profile += 1
            return data

        # we skip the existing one
        return {}

    def get_sample_fname(self, sample_name):
        fn = slugify(hashlib.sha1(sample_name.encode("utf-8")).hexdigest())
        return os.path.join(self.sample_dir, fn[:2], fn + ".sample")

    def iter_fasta(self, *fnames: str) -> Iterator[Dict[str, Union[str, int]]]:
        """
        This function iterates over the fasta files and yield a dict of selected reference and
        each sequence.

        """
        for fname in fnames:
            with (
                open_file_autodetect(fname) as handle,
                tqdm(
                    desc="Read " + fname + "...",
                    total=os.path.getsize(fname),
                    unit="bytes",
                    unit_scale=True,
                    bar_format="{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]",
                    disable=self.disable_progress,
                ) as pbar,
            ):
                seq = []
                header = None
                for line in handle:
                    pbar.update(len(line))
                    line = line.strip()
                    if line.startswith(">"):
                        if seq:
                            yield self.process_fasta_entry(header, "".join(seq), fname)
                            seq = []
                        header = line[1:]
                    else:
                        seq.append(line)
                if seq:
                    yield self.process_fasta_entry(header, "".join(seq), fname)

    def process_fasta_entry(
        self, header: str, seq: str, fname: str
    ) -> Dict[str, Union[str, int]]:
        """
        Formulate a data dict.

        Return:
            Dict
                example:
                {'name': 'OQ331004.1', 'header': 'OQ331004.1 Monkeypox virus isolate Monkeypox virus/Human/USA/CA-LACPHL-MA00393/2022,
                partial genome', 'seqhash': 'Bjhx5hv8G4m6v8kpwt4isQ4J6TQ', 'sequence': 'TACTGAAGAAW',
                'refmol': 'NC_063383.1', <-- molecule accession
                'refmolid': 1,  <-- molecule ID
                'translation_id': 1,
                'properties': {}}
        """
        try:
            sample_id = header.replace("\t", " ").replace("|", " ").split(" ")[0]
        except AttributeError:
            # Handle the 'NoneType' object has no attribute 'replace' error
            LOGGER.error("Invalid FASTA format")
            sys.exit(1)
        except Exception as e:
            LOGGER.error(f"An error occurred: {e}")
            sys.exit(1)

        refmol = self.get_refmol(header)
        if not refmol:
            # blast assignment for acession
            try:
                best_aln_dict = self.blast_best_aln[fname]
                refmol = best_aln_dict[sample_id]
                LOGGER.debug(f"Using refmol_acc: {refmol}, {sample_id}")
            except Exception as e:
                LOGGER.error(f"An error occurred: {e}")
                sys.exit(
                    f"input error: {sample_id} refers to an unknown reference molecule ({self._molregex.search(header)})."
                )
        seq = harmonize_seq(seq)
        seq = remove_charfromsequence_data(seq, char="-")
        seqhash = hash_seq(seq)
        refmolid = self.refmols[refmol]["id"]

        return {
            "name": sample_id,
            "header": header,
            "seqhash": seqhash,
            "sequence": seq,
            "refmol": refmol,
            "refmolid": refmolid,
            "translation_id": self.refmols[refmol]["translation_id"],
            "properties": "",  # self.get_properties(header),
        }

    def get_refmol(self, fasta_header):
        """

        return:
            return default_refmol_acc if cannot find mol_id from the header
        """
        mol = self._molregex.search(fasta_header)
        if mol:
            try:
                LOGGER.info(f"Using refmol_acc: {self.refmols[mol]['accession']}")
                return self.refmols[mol]["accession"]
            except Exception:
                None
        else:
            if not self.cluster_db:  # not segment gneome
                return self.default_refmol_acc
            elif self.blast_best_aln is not None:
                return None

            # if blast_best_aln is None then use default mol
            # TODO: dont return default_refmol_acc
            # return self.default_refmol_acc

            # NOTE: This code will not be triggered.... If I haven't missed anything in the logic or operation before,
            # however, I should leave the raise error as it is  in case
            # I miss something or unexpectedly event occurs.
            LOGGER.error(
                "An unexpected error occurred at def get_refmol, Please contact us.",
                exc_info=True,
            )
            raise

    def get_refseq(self, refmol_acc):
        try:
            return self.refmols[refmol_acc]["sequence"]
        except Exception:
            return None

    def get_refseq_id(self, refmol_acc):
        try:
            return self.refmols[refmol_acc]["id"]
        except Exception:
            return None

    def add_data_files(
        self, data: Dict[str, Any], seqhash: str, refseq_acc: str
    ) -> Dict[str, Any]:
        """This function linked to the add_fasta

        Create dict to store all related output file.
        and it calls sub function to create all related files.

        Args:
            data (dict): The data for the sample.
            seqhash (str): The sequence hash, optional.
            refseq_acc (str): accession from reference table.
            method (int): alignment method
        """

        # NOTE: It seems the current version didnt update variants if there is the new one (data["seqhash"] != seqhash)

        # TODO: Have to check this again and fix it if it was not correct.
        # 1. force update?

        # In cases:
        # 1. sample is reuploaded under the same name but changes in sequence (fasta)
        # 2. New Sample (no algnid found in database)
        if self.allow_updates or data["algnid"] is None or data["seqhash"] != seqhash:
            data["seqfile"] = self.cache_sequence(data["seqhash"], data["sequence"])

            data["reffile"] = self.cache_reference(
                refseq_acc, self.get_refseq(data["refmol"])
            )

            # We now use Biopython
            # data["ttfile"] = self.cache_translation_table(data["translation_id"])
            data["liftfile"] = self.cache_lift(
                refseq_acc, data["refmol"], self.get_refseq(data["refmol"])
            )

            # cache_cds is used for frameshift detection
            # but this will be removed soon, since we use snpEff.
            data["cdsfile"] = None  # self.cache_cds(refseq_acc, data["refmol"])
            data["varparquetfile"] = self.get_var_parquet_fname(
                data["seqhash"] + "@" + self.get_refhash(data["refmol"])
            )
            data["varfile"] = self.get_var_fname(
                data["seqhash"] + "@" + self.get_refhash(data["refmol"])
            )

        else:
            # In cases:
            # 2. if no changed in sequence., use the existing cache and ID
            # 3. if different samples but have similar sequence/varaint, use exiting alignID and map back to sample
            data["seqhash"] = None
            data["seqfile"] = None
            data["reffile"] = None
            data["liftfile"] = None
            data["cdsfile"] = None
            data["varparquetfile"] = None
            data["varfile"] = None

        # annotation.
        data["vcffile"] = os.path.join(
            self.anno_dir,
            get_fname(
                refseq_acc + "@" + data["name"],
                extension=".vcf",
                enable_parent_dir=True,
            ),
        )
        data["anno_vcf_file"] = os.path.join(
            self.anno_dir,
            get_fname(
                refseq_acc + "@" + data["name"],
                extension=".anno.vcf",
                enable_parent_dir=True,
            ),
        )

        return data

    def iter_samples(self, _samplefiles):
        for fname in _samplefiles:
            yield self.read_pickle(fname)

    def cache_sequence(self, seqhash, sequence):
        fname = self.get_seq_fname(seqhash)
        seqfasta = f">{seqhash}\n{sequence}\n"
        # checks if a file with the generated name (fname) already exist
        if os.path.exists(fname):
            if file_collision(fname, seqfasta):
                LOGGER.error("seqhash collision: file name:" + fname + ".")
                sys.exit(
                    "seqhash collision: sequences differ for seqhash " + seqhash + "."
                )
        else:
            try:
                with open(fname, "w") as handle:
                    handle.write(seqfasta)
            except OSError:
                os.makedirs(os.path.dirname(fname), exist_ok=True)
                with open(fname, "w") as handle:
                    handle.write(seqfasta)
        return fname

    def cache_reference(self, refid, sequence):
        fname = self.get_ref_fname(refid)
        if refid not in self._refs:
            with open(fname, "w") as handle:
                handle.write(">" + refid + "\n" + sequence + "\n")
            self._refs.add(refid)
        return fname

    def cache_lift(self, refseq_acc, refmol_acc, sequence):
        """
        The function takes in a reference id, a reference molecule accession number,
        and a reference sequence. It then checks to see if the reference molecule accession number is in the set of molecules that
        have been cached. If it is not, it iterates through all of the coding sequences for that molecule and creates a
        dataframe for each one.
        It then saves the dataframe to a pickle file and adds the reference molecule accession number to
        the set of molecules that have been cached.
        It then returns the name of the pickle file.
        """
        rows = []
        # cache self._lifts
        if refmol_acc in self._lifts:
            # Reuse the cached dataframe
            return self._lifts[refmol_acc]
        else:
            cols = [
                "elemid",
                "nucPos1",
                "nucPos2",
                "nucPos3",
                "ref1",
                "ref2",
                "ref3",
                "alt1",
                "alt2",
                "alt3",
                "symbol",
                "accession",
                "aaPos",
                "aa",
            ]
            # if there is no cds, the lift file will not be generated
            for cds in self.iter_cds_v2(refmol_acc):
                LOGGER.debug(cds)
                try:
                    elemid = cds["id"]
                    symbol = cds["symbol"]
                    accession = cds["accession"]
                    full_seq = cds["sequence"] + "*"  # Full cds sequence
                    coords = [
                        list(group)
                        for group in zip_longest(
                            *[iter(self.get_cds_coord_list(cds))] * 3, fillvalue="-"
                        )
                    ]  # provide a list of triplets for all CDS coordinates
                    # seq = list(reversed(cds["sequence"] + "*"))
                    seq = list(full_seq)  # Convert AA sequence to list for tracking
                    for aa_pos, nuc_pos_list in enumerate(coords):
                        rows.append(
                            [elemid]
                            + nuc_pos_list
                            + [
                                sequence[nuc_pos_list[0]],
                                sequence[nuc_pos_list[1]],
                                sequence[nuc_pos_list[2]],
                            ]
                            * 2
                            + [symbol, accession, aa_pos, seq[aa_pos]]
                        )

                except Exception as e:
                    LOGGER.error("\n------- Fatal Error ---------")
                    LOGGER.error(traceback.format_exc())
                    LOGGER.error("\nDebugging Information:")
                    LOGGER.error(e)
                    LOGGER.error("\n During insert:")
                    LOGGER.error(cds)
                    sys.exit(1)

            df = pd.DataFrame.from_records(rows, columns=cols, coerce_float=False)
            df = df.reindex(df.columns.tolist(), axis=1)
            # df.to_pickle(fname)

            self._lifts[refmol_acc] = df
            return df

    def get_cds_fname(self, refid):
        return os.path.join(self.ref_dir, str(refid) + ".lcds")

    def get_seq_fname(self, seqhash):
        fn = slugify(seqhash)
        return os.path.join(self.seq_dir, fn[:2], fn + ".seq")

    def get_ref_fname(self, refid):
        return os.path.join(self.ref_dir, str(refid) + ".seq")

    def get_lift_fname(self, refid):
        return os.path.join(self.ref_dir, str(refid) + ".lift")

    def get_tt_fname(self, refid):
        return os.path.join(self.ref_dir, str(refid) + ".tt")

    def get_algn_fname(self, seqhash):
        fn = slugify(seqhash)
        return os.path.join(self.algn_dir, fn[:2], fn + ".algn")

    def get_var_parquet_fname(self, seqhash):
        fn = slugify(seqhash)
        return os.path.join(self.var_dir, fn[:2], fn + ".var.parquet")

    def get_var_fname(self, seqhash):
        fn = slugify(seqhash)
        return os.path.join(self.var_dir, fn[:2], fn + ".var")

    def iter_cds_v2(self, refmol_acc):
        """
        Extracts CDS sequences and their corresponding genomic coordinates.
        """
        cds = {}
        prev_elem = None
        if self.is_segment_import:
            gene_rows = APIClient(base_url=self.base_url).get_elements(
                molecule_acc=refmol_acc
            )
        else:
            gene_rows = APIClient(base_url=self.base_url).get_elements(
                ref_acc=refmol_acc
            )

        for row in gene_rows:
            for cds_entry in row["cds_list"]:  # Iterate through cds_list
                if prev_elem is None:
                    prev_elem = cds_entry["cds.id"]
                elif cds_entry["cds.id"] != prev_elem:
                    yield cds
                    cds = {}
                    prev_elem = cds_entry["cds.id"]

                if not cds:
                    cds = {
                        "id": cds_entry["cds.id"],
                        "accession": cds_entry["cds.accession"],
                        "symbol": row["gene.gene_symbol"],  # Gene symbol from gene
                        "sequence": cds_entry["cds.sequence"],  # Protein sequence
                        "ranges": [
                            (
                                segment["cds_segment.start"],
                                segment["cds_segment.end"],
                                (
                                    1 if segment["cds_segment.forward_strand"] else -1
                                ),  # Convert bool to strand
                            )
                            for segment in cds_entry[
                                "cds_segments"
                            ]  # Extract ranges from cds_segments
                        ],
                    }

        if cds:
            yield cds

    def get_cds_coord_list(self, cds: dict) -> List[int]:
        """
        Return a ordered list of all genomic positions for the repsctive CDS.

        Args:
            cds (dict): The cds dictionary.

        Returns:
            List[int]:
                list of integers representig the genomic coding positions in order.
        """
        coords = []
        for data in cds["ranges"]:
            if data[-1] == 1:
                coords.extend(list(range(data[0], data[1])))
            else:
                coords.extend(list(range(data[0], data[1]))[::-1])

        return coords

    def get_refhash(self, refmol_acc: str) -> Optional[str]:
        """
        Get the sequence hash for a given reference molecule accession number.

        Args:
            refmol_acc (str): The reference molecule accession number.

        Returns:
            str/None: The sequence hash if found, or None if not found.
        """
        try:
            if "seqhash" not in self.refmols[refmol_acc]:
                self.refmols[refmol_acc]["seqhash"] = hash_seq(
                    self.refmols[refmol_acc]["sequence"]
                )
            return self.refmols[refmol_acc]["seqhash"]
        except Exception:
            return None

    def perform_paranoid_cached_samples(  # noqa: C901
        self, sample_data_dict_list, must_pass_paranoid, chunk_size=50, n_jobs=8
    ) -> list:
        """
        This function performs the paranoid test without fetching variants from the database.
        It will read the var file and compare it with the original sequence.
        Combination of 'import_cached_samples' and 'paranoid_check' function

        Parallelized using mpire WorkerPool for improved performance.

        Args:
            sample_data_dict_list: List of sample data dictionaries
            must_pass_paranoid: Whether to exit if paranoid tests fail
            chunk_size: Number of samples to process in each batch
            n_jobs: Maximum number of worker processes

        Return:
            list[Dict]: List of dict sample.
        """
        list_fail_samples = []
        passed_samples_list = []
        total_samples = len(sample_data_dict_list)

        # Create batches for parallel processing
        batches = [
            sample_data_dict_list[i : i + chunk_size]
            for i in range(0, len(sample_data_dict_list), chunk_size)
        ]

        # Prepare data that workers will need from this instance
        cache_instance_data = {"refmols": self.refmols, "error_dir": self.error_dir}

        # Prepare batch data for workers
        batch_data_list = [(batch, self.error_dir) for batch in batches]

        # Use mpire WorkerPool for multiprocessing
        with WorkerPool(n_jobs=n_jobs, shared_objects=cache_instance_data) as pool:
            # Process with progress bar
            with tqdm(
                total=total_samples,
                desc="Paranoid Check...",
                unit="samples",
                bar_format="{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]",
                disable=self.disable_progress,
            ) as pbar:
                # Use imap for processing with progress updates
                for batch_passed, batch_failed in pool.imap_unordered(
                    process_paranoid_batch_worker,
                    batch_data_list,
                ):
                    passed_samples_list.extend(batch_passed)
                    list_fail_samples.extend(batch_failed)

                    # Update progress bar
                    batch_size = len(batch_passed) + len(batch_failed)
                    pbar.update(batch_size)

        count_sample = total_samples - len(list_fail_samples)
        LOGGER.info(f"Total passed samples: {count_sample}")

        if list_fail_samples:
            LOGGER.warning(
                "Some samples fail in sanity check; please check import.log under the cache directory."
            )
            # LOGGER.info(f"Total Fail: {len(list_fail_samples)}.")

            # NOTE: comment this part, for now, we need to discuss which
            # information we want to report for the failed sample.
            # self.paranoid_align_multi(list_fail_samples, threads)

            # currently, we report only failed sample IDs.
            self.error_logfile_obj.write("Fail sample during alignment:----\n")
            LOGGER.warning("Failed sample IDs:")
            for fail_sample in list_fail_samples:
                self.error_logfile_obj.write(f"{fail_sample['sample_name']}\n")
                LOGGER.warning(fail_sample["sample_name"])
            if must_pass_paranoid:
                sys.exit("Some sequences failed the paranoid test, aborting.")

        return passed_samples_list

    def build_snpeff_cache(self, reference):  # noqa: C901
        """Build snpEff cache for the given reference,
        supporting both single and multiple GenBank files (segments).

        1. Request the GBK file (or ZIP if segment).
        2. Extract accession versions from GenBank headers.
        3. Create folders for each replicon using accession versions.
        4. Update snpEff.config with replicon accessions.
        5. Build the snpEff cache for each replicon.
        """
        params = {
            "reference": reference,
        }

        if os.path.exists(os.path.join(self.snpeff_data_dir, reference, ".done")):
            # for multiple replicons, we assume if there is a refernce accesion and .done file,
            # Thery are already built.
            LOGGER.info(f"snpEff cache for reference {reference} is already built.")
            return True

        response = APIClient(base_url=self.base_url).get_reference_genbank(params)
        if response.status_code == 200:
            LOGGER.info("----------- Build snpEff cache -----------")
            gbk_files = []
            # Check if response is a ZIP file (multiple segments) or a single GBK
            content_type = response.headers.get("Content-Type", "")
            snpeff_data_dir_tmp = os.path.join(self.snpeff_data_dir, "tmp")
            os.makedirs(snpeff_data_dir_tmp, exist_ok=True)

            if "zip" in content_type:  # Zip file, Multi GBK files
                zip_path = os.path.join(snpeff_data_dir_tmp, f"{reference}.segment.zip")
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Extract ZIP file
                with zipfile.ZipFile(zip_path, "r") as zipf:
                    zipf.extractall(snpeff_data_dir_tmp)
                    gbk_files = [
                        os.path.join(snpeff_data_dir_tmp, f) for f in zipf.namelist()
                    ]
                LOGGER.debug(f"Detect segment genome, all GBKs: {gbk_files}")
            else:
                # Single GBK file
                gbk_file = os.path.join(snpeff_data_dir_tmp, f"{reference}.gbk")
                os.makedirs(os.path.dirname(gbk_file), exist_ok=True)
                with open(gbk_file, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                gbk_files = [gbk_file]

            # Extract accession versions and organize files
            replicon_accessions = []
            for gbk_file in gbk_files:
                with open(gbk_file, "r") as f:
                    for line in f:
                        if line.startswith("VERSION"):
                            accession = line.split()[1]
                            replicon_accessions.append(accession)
                            break
                # Create a folder for each replicon and move the file
                replicon_dir = os.path.join(self.snpeff_data_dir, accession)
                os.makedirs(replicon_dir, exist_ok=True)
                shutil.move(gbk_file, os.path.join(replicon_dir, "genes.gbk"))
            LOGGER.info(f"Replicon accession: {replicon_accessions}")

            # Update snpEff.config with replicon accessions
            for replicon_accession in replicon_accessions:
                self.update_snpeff_config(replicon_accession)

            # Build snpEff cache for each segment
            for replicon_accession in replicon_accessions:
                # get folder name from gbk_file since it represents an each accession
                replicon_dir = os.path.join(self.snpeff_data_dir, replicon_accession)
                _done_file = os.path.join(replicon_dir, ".done")
                # Skip if already built
                if os.path.exists(_done_file):
                    LOGGER.info(
                        f"snpEff cache for {replicon_accession} already exists, skipping..."
                    )
                    continue

                cmd = [
                    "snpEff",
                    "build",
                    "-nodownload",
                    replicon_accession,
                    "-genbank",
                    "-dataDir",
                    self.snpeff_data_dir,
                ]

                LOGGER.info(f"Building snpEff cache for {replicon_accession}")
                try:
                    subprocess.run(cmd, capture_output=True, check=True)
                    # Mark this segment as done
                    with open(_done_file, "w") as f:
                        f.write("done")

                except subprocess.CalledProcessError as e:
                    LOGGER.error(
                        f"Failed to build snpEff for {replicon_accession}: {e}"
                    )
                    sys.exit(1)

            # remove tmp folder
            shutil.rmtree(snpeff_data_dir_tmp)
            LOGGER.info("----------- Done -----------")
            return True
        else:
            LOGGER.error(f"Cannot get genbank file for reference {reference}")
            return False

    def find_snpeff_config(self):
        """Finds the latest snpEff.config file in the active Conda environment."""
        conda_env_dir = os.getenv("CONDA_PREFIX")

        if not conda_env_dir:
            LOGGER.error("No conda environment is currently activated.")
            sys.exit(1)

        # Look for snpEff-* directories inside 'share'
        share_path = os.path.join(conda_env_dir, "share")
        snpeff_versions = sorted(
            glob.glob(os.path.join(share_path, "snpeff-*")), reverse=True
        )

        if not snpeff_versions:
            LOGGER.error("No snpEff installation found in the Conda environment.")
            sys.exit(1)
        else:
            LOGGER.debug(
                f"Found {snpeff_versions} snpEff installations in the Conda environment."
            )
        # Take the latest version directory
        latest_snpeff_dir = snpeff_versions[0]
        config_path = os.path.join(latest_snpeff_dir, "snpEff.config")

        if not os.path.exists(config_path):
            LOGGER.error(f"snpEff.config not found in {latest_snpeff_dir}")
            sys.exit(1)

        return config_path

    def update_snpeff_config(self, reference):
        """Updates snpEff.config by adding a new reference genome."""
        config_file = self.find_snpeff_config()
        genome_entry = f"{reference}.genome : {reference}"

        with open(config_file, "r") as f:
            lines = f.readlines()

        # Check if reference already exists
        if any(genome_entry in line for line in lines):
            LOGGER.debug(f"{reference} is already present in {config_file}.")
        else:
            # Append new reference
            with open(config_file, "a") as f:
                f.write(f"\n{genome_entry}\n")

            LOGGER.debug(f"Added '{genome_entry}' to {config_file}.")
