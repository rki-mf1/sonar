from contextlib import contextmanager
import gzip
from hashlib import sha256
import lzma
import os
import sys
from typing import List
from typing import Union
import zipfile

from Bio.Seq import Seq
import magic


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
