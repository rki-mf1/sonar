import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import datetime
import gzip
import hashlib
from hashlib import sha256
from itertools import islice
import lzma
import os
import shutil
import sys
import traceback
from typing import List
from typing import Union
import zipfile

from Bio.Seq import Seq
import magic
from sonar_cli.logging import LoggingConfigurator

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()


@contextmanager
def open_file_autodetect(file_path: str, mode: str = "r"):
    """
    Opens a file with automatic packing detection.

    Args:
        file_path: The path of the file to open.
        mode: The mode in which to open the file. Default is 'r' (read mode).

    Returns:
        A context manager yielding a file object.
    """
    # Use the magic library to identify the file type
    file_type = magic.from_file(file_path, mime=True)

    if file_type == "application/x-xz":
        file_obj = lzma.open(file_path, mode + "t")  # xz
    elif file_type == "application/gzip":
        file_obj = gzip.open(file_path, mode + "t")  # gz
    elif file_type == "application/zip":
        zip_file = zipfile.ZipFile(file_path, mode)  # zip
        # Assumes there's one file in the ZIP, adjust as necessary
        file_obj = zip_file.open(zip_file.namelist()[0], mode)
    elif file_type == "text/plain" or file_type == "application/csv":  # plain
        file_obj = open(file_path, mode)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    try:
        yield file_obj
    finally:
        file_obj.close()
        if file_type == "application/zip":
            zip_file.close()


def hash_seq(seq: Union[str, Seq]) -> str:
    """
    Generate a hash from a sequence.

    Args:
        seq: The sequence to hash. This can either be a string or a Seq object from BioPython.

    Returns:
        The SHA-256 hash of the sequence.

    Notes:
        The SHA-256 hash algorithm is used as it provides a good balance
        between performance and collision resistance.
    """
    # If the input is a BioPython Seq object, convert it to a string.
    if isinstance(seq, Seq):
        seq = str(seq)

    return sha256(seq.upper().encode()).hexdigest()


def harmonize_seq(seq: str) -> str:
    """
    Harmonizes the input sequence.

    This function trims leading and trailing white spaces, converts the sequence to upper case and
    replaces all occurrences of "U" with "T". It's usually used to standardize the format of a DNA
    or RNA sequence.

    Args:
        seq (str): The input sequence as a string.

    Returns:
        str: The harmonized sequence.
    """
    try:
        return seq.strip().upper().replace(".", "N").replace("U", "T")
    except AttributeError as e:
        raise ValueError(
            f"Invalid input, expected a string, got {type(seq).__name__}"
        ) from e


def remove_charfromsequence_data(seq: str, char="-") -> str:
    """
    Removes specified character from the sequence data.

    Args:
        seq (str): The input sequence data.
        char (str): The character to be removed. If empty, removes all occurrences of '-'. Default is empty.

    Returns:
        str: The sequence data with specified characters removed.
    """

    return seq.replace(char, "")


def read_seqcache(fname):
    with open(fname, "r") as handle:
        seq = handle.readline().strip()
    return seq


def get_filename_sonarhash(outfile):
    filename_sonarhash = os.path.splitext(outfile)[0] + ".sonar_hash"
    return filename_sonarhash


def _get_csv_colnames(fname: str, delim: str) -> List[str]:
    """
    Retrieve the column names of a CSV file.

    Args:
        fname: Filename of the CSV file.
        delim: Delimiter used in the CSV file.

    Returns:
        List of column names.
    """
    with open_file_autodetect(fname) as file:
        return file.readline().strip().split(delim)


@contextmanager
def out_autodetect(outfile=None):
    """
    Open a file if the 'outfile' is provided.
    If not, use standard output.

    Args:
        outfile: File path to the output file. If None, use standard output.
    """
    if outfile is not None:
        f = open(outfile, "w")
    else:
        f = sys.stdout
    try:
        yield f
    except BrokenPipeError:
        # Python flushes standard streams on exit; redirect remaining output
        # to devnull to avoid another BrokenPipeError at shutdown
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    finally:
        if f is not sys.stdout:
            f.close()


def write_to_log(logfile, msg, die=False, errtype="error"):
    if logfile:
        logfile.write(msg + "\n")
    elif not die:
        sys.stderr.write(msg + "\n")
    else:
        exit(errtype + ": " + msg)


def read_var_file(var_file: str, exclude_var_type: str = "", showNX: bool = False):
    iter_dna_list = []
    with open(var_file, "r") as handle:
        for line in handle:
            if line == "//":
                break
            vardat = line.strip("\r\n").split("\t")
            if vardat[6] == exclude_var_type:
                continue
            else:

                if not showNX and (vardat[3] == "N" or vardat[3] == "X"):
                    continue

                iter_dna_list.append(
                    {
                        "variant.ref": vardat[0],  # ref
                        "variant.alt": vardat[3],  # alt
                        "variant.start": int(vardat[1]),  # start
                        "variant.end": int(vardat[2]),  # end
                        "variant.reference": vardat[4],  # ref
                        "variant.lable": vardat[5],  # lable
                        "variant.type": vardat[6],  # type
                    }  # frameshift
                )
    return iter_dna_list


def flatten_json_output(result_data: list, exclude_annotation=False):
    flattened_data = []
    # Load JSON data

    for result in result_data:
        flattened_entry = {
            "name": result.get("name", ""),
        }

        for prop in result.get("properties", []):
            flattened_entry[prop["name"]] = prop["value"]

        if exclude_annotation:
            flattened_entry["genomic_profiles"] = " ".join(
                result.get("genomic_profiles", [])
            )
        else:
            flattened_entry["genomic_profiles"] = " ".join(
                [
                    f"{key}'({', '.join(value)})'" if value else f"{key}"
                    for key, value in result["genomic_profiles"].items()
                ]
            )

        flattened_entry["proteomic_profiles"] = " ".join(
            result.get("proteomic_profiles", [])
        )
        flattened_data.append(flattened_entry)

    return flattened_data


def combine_sample_argument(samples: List[str] = [], sample_files: List[str] = []):
    samples = set([x.strip() for x in samples])
    for fname in sample_files:
        _files_exist(fname)
        with open_file_autodetect(fname) as handle:
            for line in handle:
                samples.add(line.strip())

    return list(samples)


def _files_exist(*files: str, exit_on_fail=True) -> bool:
    """
    Check if a given file path exists.

    Args:
        files (string): The name and path to an existing file  with unpacking (*), each element of the list becomes a separate argument
        exit_on_fail (boolean): Whether to exit the script if the file doesn't exist.
        Default is True.

    Returns:
        True if the file exists, False otherwise.
    """

    for fname in files:
        if not os.path.isfile(fname):
            LOGGER.error(f"The file '{fname}' does not exist.")
            if exit_on_fail:
                sys.exit(1)
            return False
    return True


def get_current_time(format="%d.%b %Y %H:%M:%S"):
    """
    Get the current time in the specified format.

    Args:
        format (str): The format to represent the datetime string.
            Default is "%d.%b %Y %H:%M:%S".

    Returns:
        str: The current time formatted according to the specified format.
    """
    return datetime.datetime.now().strftime(format)


def calculate_time_difference(start_time, end_time, format="%d.%b %Y %H:%M:%S"):
    """
    Calculate the time difference between two timestamps.

    Args:
        start_time (str): The start timestamp.
        end_time (str): The end timestamp.
        format (str): The format of the timestamps. Default is "%d.%b %Y %H:%M:%S".

    Returns:
        datetime.timedelta: The time difference between start and end timestamps.
    """
    start_datetime = datetime.datetime.strptime(start_time, format)
    end_datetime = datetime.datetime.strptime(end_time, format)
    return end_datetime - start_datetime


def slugify(string):
    return base64.urlsafe_b64encode(string.encode("UTF-8")).decode("UTF-8").rstrip("=")


def file_collision(fname, data):
    with open(fname, "r") as handle:
        if handle.read() != data:
            return True
    return False


def chunk(arr_range, arr_size):
    arr_range = iter(arr_range)
    return iter(lambda: tuple(islice(arr_range, arr_size)), ())


def clear_sample_cache(sample):
    try:
        if sample["mafft_seqfile"] is not None:
            try:
                os.remove(sample["mafft_seqfile"])
            except FileNotFoundError:
                pass  # File was already deleted
        try:
            os.remove(sample["vcffile"] + ".gz")
        except FileNotFoundError:
            pass
        try:
            os.remove(sample["vcffile"] + ".gz.tbi")
        except FileNotFoundError:
            pass
        # if os.path.exists(sample["vcffile"]):
        #     os.remove(sample["vcffile"])
        # if sample["anno_vcf_file"]:
        #    os.remove(sample["anno_vcf_file"])
        # if sample["anno_tsv_file"]:
        #    os.remove(sample["anno_tsv_file"])
    except (TypeError, OSError) as e:
        LOGGER.error(traceback.format_exc())
        LOGGER.error("\nDebugging Information:")
        LOGGER.error(e)
        LOGGER.error("-----------")
        LOGGER.error(sample)


def clear_unnecessary_cache(samples, max_workers=4):
    # I used ThreadPoolExecutorfor simplicity
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(clear_sample_cache, samples)


def get_fname(name, extension="", enable_parent_dir=False):
    fn = slugify(hashlib.sha1(str(name).encode("utf-8")).hexdigest())

    if enable_parent_dir:
        return os.path.join(fn[:2], fn + extension)
    else:
        return fn + extension


def copy_file(src, dest):
    """
    Copies a file from the source path to the destination path.

    Parameters:
    src (str): The path to the source file.
    dest (str): The path to the destination directory.

    Returns:
    None
    """
    if not os.path.isfile(src):
        raise FileNotFoundError(f"The source file {src} does not exist.")

    if not os.path.isdir(dest):
        raise NotADirectoryError(f"The destination directory {dest} does not exist.")

    # Construct the new file path
    new_file_path = os.path.join(dest, os.path.basename(src))

    # Copy the file
    shutil.copy(src, new_file_path)
    LOGGER.info(f"File {src} has been copied to {dest}")
    # Return the new file path
    return new_file_path
