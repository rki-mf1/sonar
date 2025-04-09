from dataclasses import dataclass
import pathlib
import re
import uuid

from dateutil import parser
from django.core.files.uploadedfile import InMemoryUploadedFile

from . import models

IUPAC_CODES = {
    "nt": {
        "A": set("A"),
        "C": set("C"),
        "G": set("G"),
        "T": set("T"),
        "R": set("AGR"),
        "Y": set("CTY"),
        "S": set("GCS"),
        "W": set("ATW"),
        "K": set("GTK"),
        "M": set("ACM"),
        "B": set("CGTB"),
        "D": set("AGTD"),
        "H": set("ACTH"),
        "V": set("ACGV"),
        "N": set("ACGTRYSWKMBDHVN"),
        "n": set("N"),
    },
    "aa": {
        "A": set("A"),
        "R": set("R"),
        "N": set("N"),
        "D": set("D"),
        "C": set("C"),
        "Q": set("Q"),
        "E": set("E"),
        "G": set("G"),
        "H": set("H"),
        "I": set("I"),
        "L": set("L"),
        "K": set("K"),
        "M": set("M"),
        "F": set("F"),
        "P": set("P"),
        "S": set("S"),
        "T": set("T"),
        "W": set("W"),
        "Y": set("Y"),
        "V": set("V"),
        "U": set("U"),
        "O": set("O"),
        "B": set("DNB"),
        "Z": set("EQZ"),
        "J": set("ILJ"),
        "Φ": set("VILFWYMΦ"),
        "Ω": set("FWYHΩ"),
        "Ψ": set("VILMΨ"),
        "π": set("PGASπ"),
        "ζ": set("STHNQEDKRζ"),
        "+": set("KRH+"),
        "-": set("DE-"),
        "X": set("ARNDCQEGHILKMFPSTWYVUOBZJΦΩΨπζ+-X"),
        "x": set("X"),
    },
}

regexes = {
    "snv": re.compile(r"^(\^*)(|[^:]+:)?([^:]+:)?([A-Z]+)([0-9]+)(=?[A-Zxn]+)$"),
    "del": re.compile(r"^(\^*)(|[^:]+:)?([^:]+:)?del:(=?[0-9]+)(|-=?[0-9]+)?$"),
}


def write_to_file(_path: pathlib.Path, file_obj: InMemoryUploadedFile):
    _path.parent.mkdir(exist_ok=True, parents=True)
    with open(_path, "wb") as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)


# distutils will no longer be part of the standard library,
# here is the code for distutils.util.strtobool() (see the source code for 3.11.2).
def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))


def resolve_ambiguous_NT_AA(type, char):
    try:
        selected_chars = list(IUPAC_CODES[type][char])
    except KeyError:
        raise KeyError(f"Invalid notation '{char}'.")

    return selected_chars


def define_profile(mutation):  # noqa: C901
    """
    Parse and validate mutation profile.
    """
    _query = {"label": ""}
    match = None
    for mutation_type, regex in regexes.items():
        match = regex.match(mutation)
        if match:
            gene_name = match.group(3)[:-1] if match.group(3) else None

            if mutation_type == "snv":
                alt = match.group(6)
                ref = match.group(4)

                # Validate alternates based on IUPAC codes
                alt_is_aa = all(c in IUPAC_CODES["aa"] for c in alt)
                alt_is_nt = all(c in IUPAC_CODES["nt"] for c in alt)

                if gene_name:  # AA mutation
                    if not alt_is_aa:
                        raise ValueError(
                            f"Invalid AA mutation: '{alt}' contains non-AA characters."
                        )
                    if ref not in IUPAC_CODES["aa"]:
                        raise ValueError(
                            f"Invalid AA reference: '{ref}' is not a valid amino acid."
                        )
                    _query["alt_aa"] = alt
                    _query["ref_aa"] = ref
                    _query["ref_pos"] = match.group(5)
                    _query["protein_symbol"] = gene_name
                    _query["label"] = "SNP AA" if len(alt) == 1 else "Ins AA"
                else:  # NT mutation
                    if not alt_is_nt or ref not in IUPAC_CODES["nt"]:
                        error_message = (
                            f"Invalid NT mutation: '{alt}' contains non-NT characters."
                            if not alt_is_nt
                            else f"Invalid NT reference: '{ref}' is not a valid nucleotide."
                        )

                        if alt_is_aa:
                            error_message = (
                                error_message
                                + "\n"
                                + "Did you mean an AA query? Querying for AA mutations without specifying a gene name is not allowed."
                            )
                        raise ValueError(error_message)

                        sys.exit(1)
                    _query["alt_nuc"] = alt
                    _query["ref_nuc"] = ref
                    _query["ref_pos"] = match.group(5)
                    _query["label"] = "SNP Nt" if len(alt) == 1 else "Ins Nt"

            elif mutation_type == "del":
                _query["first_deleted"] = match.group(4)
                _query["last_deleted"] = match.group(5)[1:]

                if gene_name:  # AA deletion
                    _query["protein_symbol"] = gene_name
                    _query["label"] = "Del AA"
                else:  # NT deletion
                    _query["label"] = "Del Nt"

            # Flag for exclusion
            negate = True if match.group(1) else False
            _query["exclude"] = negate
            break

    if not match:
        raise ValueError(f"Invalid mutation notation '{mutation}'.")

    return _query


@dataclass
class PropertyColumnMapping:
    db_property_name: str
    data_type: str
    default: any


def generate_job_ID(is_prop: bool):
    job = str(uuid.uuid4())

    if is_prop:
        job_id = "cli_prop_" + job
    else:
        job_id = "cli_" + job
    return job_id


def parse_date(value):
    # Generalized function to parse any date format
    # exp. 2021-11-30T00:00:00, 2021-02-16 19:00:03 +0100
    # 2/2/2021
    if not value or str(value).strip() == "":
        return None
    try:
        parsed_date = parser.parse(value)
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"ValueError: Unable to parse date from '{value}'")
    except TypeError:
        raise TypeError(f"TypeError: Invalid type for date parsing - '{value}'")
    # or return None?
    # raise ValueError(f"Failed to parse date '{value}': {str(e)}") from e


def get_distinct_gene_symbols(reference=None):
    """
    Helper method to get distinct gene symbols.
    This method can be called from anywhere.
    """
    queryset = models.Gene.objects.distinct("gene_symbol").values("gene_symbol")
    if reference:
        queryset = queryset.filter(replicon__reference__accession=reference)
    return [item["gene_symbol"] for item in queryset]


def parse_default_data(value):
    # Convert "None", "null", or empty strings to Python None
    if value in {"None", "null", ""}:
        return None
    return value
