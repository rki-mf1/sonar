from dataclasses import dataclass
import pathlib
import re
import uuid

from dateutil import parser
from django.core.files.uploadedfile import InMemoryUploadedFile
import pandas as pd
from rest_framework import status
from rest_framework.response import Response

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
    # 1. A435G (NT)
    # 2. NC_026438.1:A435G (Replicon:NT)
    # 3. SH:K53E (Gene:AA)
    # 4. NC_026438.1:SH:K53E (Replicon:Gene:AA)
    "snv": re.compile(
        r"^(\^*)"  # group 1: negation (optional)
        r"(?:([A-Za-z0-9_.-]+):)?"  # group 2: replicon accession (optional)
        r"(?:([A-Za-z0-9_.-]+):)?"  # group 3: gene symbol (optional)
        r"([A-Z]+)"  # group 4: Ref (NT oder AA)
        r"([0-9]+)"  # group 5: Position
        r"(=?[A-Zxn]+)$"  # group 6: Alt (NT oder AA)
    ),
    # 1. del:133177 or del:133177-133186 (NT)
    # 2. NC_026438.1:del:133177-133186 (Replicon:NT)
    # 3. SH:del:34 or SH:del:34-35 (Gene:AA)
    # 4. NC_026438.1:SH:del:34-35 (Replicon:Gene:AA)
    "del": re.compile(
        r"^(\^*)"  # group 1: negation(optional)
        r"(?:([A-Za-z0-9_.]+):)?"  # group 2: replicon accession (optional)
        r"(?:([A-Za-z0-9_-]+):)?"  # group 3: gene symbol (optional)
        r"del:"
        r"(=?[0-9]+)"  # group 4: First deleted position
        r"(?:-(=?[0-9]+))?$"  # group 5: Last deleted position (optional)
    ),
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


def define_profile(mutation: str, protein_symbols: set, replicons: set):
    """
    Parse and validate mutation profile.
    Supported formats:
    NT Mutations:
      1. A435G                           (single-segment only)
      2. NC_026438.1:A435G               (multi-segment with replicon)

    AA Mutations:
      3. SH:K53E                         (gene symbol required)
      4. NC_026438.1:SH:K53E             (replicon + gene symbol)

    Deletions:
      5. del:133177 or del:133177-133186 (NT deletion)
      6. NC_026438.1:del:133177-133186   (NT deletion with replicon)
      7. SH:del:34 or SH:del:34-35       (AA deletion)
      8. NC_026438.1:SH:del:34-35        (AA deletion with replicon+gene)
    """
    _query = {"label": ""}
    match = None
    for mutation_type, regex in regexes.items():
        match = regex.match(mutation)
        if match:
            negate = match.group(1)  # ^ for exclusion
            first_id = match.group(2)  # Could be replicon OR gene
            second_id = match.group(3)  # Could be gene OR None
            # IMPORTANT: determine gene or replicon
            replicon_accession = None
            gene_name = None
            # case 1: both groups, e.g. CY121680.1:HA:S220T
            if first_id and second_id:
                if first_id in replicons:
                    replicon_accession = first_id
                    if second_id in protein_symbols:
                        gene_name = second_id
                    else:
                        raise ValueError(
                            f"Invalid gene symbol: '{second_id}'. "
                            f"Valid genes: {', '.join(sorted(list(protein_symbols))[:10])}..."
                        )
                else:
                    raise ValueError(
                        f"Invalid replicon accession: '{first_id}'. "
                        f"Valid replicons: {', '.join(sorted(list(replicons))[:10])}..."
                    )

            # case 2: only one group, e.g HA:S220T or NC_026438.1:A435G
            elif first_id and not second_id:
                if first_id in protein_symbols:
                    gene_name = first_id
                elif first_id in replicons:
                    replicon_accession = first_id
                else:
                    raise ValueError(
                        f"Unknown identifier: '{first_id}'. "
                        f"Not a valid replicon or gene name.\n"
                        f"Valid genes: {', '.join(sorted(list(protein_symbols))[:5])}...\n"
                        f"Valid replicons: {', '.join(sorted(list(replicons))[:5])}..."
                    )
            # case 3: no group, e.g A435G, → gene_name and replicon_accession == None
            if mutation_type == "snv":
                ref = match.group(4)
                ref_pos = match.group(5)
                alt = match.group(6)

                # Validate alternates based on IUPAC codes
                alt_is_aa = all(c in IUPAC_CODES["aa"] for c in alt)
                alt_is_nt = all(c in IUPAC_CODES["nt"] for c in alt)
                ref_is_aa = ref in IUPAC_CODES["aa"]
                ref_is_nt = ref in IUPAC_CODES["nt"]

                # Determine if AA or NT mutation
                if gene_name:
                    # AA MUTATION (gene_symbol:ref_aa+pos+alt_aa)
                    if not alt_is_aa:
                        raise ValueError(
                            f"Invalid AA mutation: '{alt}' contains non-AA characters."
                        )
                    if not ref_is_aa:
                        raise ValueError(
                            f"Invalid AA reference: '{ref}' is not a valid amino acid."
                        )

                    _query["alt_aa"] = alt
                    _query["ref_aa"] = ref
                    _query["ref_pos"] = ref_pos
                    _query["protein_symbol"] = gene_name
                    _query["label"] = "SNP AA" if len(alt) == 1 else "Ins AA"
                    _query["replicon_accession"] = replicon_accession

                else:
                    # NT MUTATION (ref_nuc+pos+alt_nuc)
                    if not alt_is_nt or not ref_is_nt:
                        error_message = (
                            f"Invalid NT mutation: '{alt}' contains non-NT characters."
                            if not alt_is_nt
                            else f"Invalid NT reference: '{ref}' is not a valid nucleotide."
                        )

                        if alt_is_aa and ref_is_aa:
                            error_message += (
                                "\nDid you mean an AA query? "
                                "AA mutations require a gene symbol (e.g., HA:S220T)."
                            )
                        raise ValueError(error_message)

                    _query["alt_nuc"] = alt
                    _query["ref_nuc"] = ref
                    _query["ref_pos"] = ref_pos
                    _query["label"] = "SNP Nt" if len(alt) == 1 else "Ins Nt"
                    _query["replicon_accession"] = replicon_accession

            elif mutation_type == "del":
                first_deleted = match.group(4)
                last_deleted = match.group(5) if match.group(5) else ""
                # if gene name is provided, it's an AA deletion
                if gene_name:
                    # AA DELETION (gene:del:pos-pos)
                    _query["protein_symbol"] = gene_name
                    _query["label"] = "Del AA"
                    _query["first_deleted"] = first_deleted
                    _query["last_deleted"] = last_deleted
                    _query["replicon_accession"] = replicon_accession
                # without gene name, it's an NT deletion
                else:
                    # NT DELETION (del:pos-pos)
                    _query["label"] = "Del Nt"
                    _query["first_deleted"] = first_deleted
                    _query["last_deleted"] = last_deleted
                    _query["replicon_accession"] = replicon_accession

            # Flag for exclusion
            _query["exclude"] = True if negate else False
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
    if pd.isna(value) or not value or str(value).strip() == "":
        return pd.NA
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
    queryset = models.Gene.objects.distinct("symbol").values("symbol")
    if reference:
        queryset = queryset.filter(replicon__reference__accession=reference)
    return [item["symbol"] for item in queryset if item["symbol"]]


def get_distinct_replicon_accessions(reference=None):
    """
    Helper method to get distinct replicon accessions.
    """
    queryset = models.Replicon.objects.all()
    if reference:
        queryset = queryset.filter(reference__accession=reference)
    qs = queryset.values_list("accession", flat=True).distinct()
    return [acc for acc in qs if acc]


def get_distinct_cds_accessions(reference=None, replicon=None):
    """
    Helper method to get distinct CDS accessions.
    """
    queryset = models.CDS.objects.all()
    if replicon:
        queryset = queryset.filter(gene__replicon__accession=replicon)
    if reference:
        queryset = queryset.filter(gene__replicon__reference__accession=reference)
    qs = queryset.values_list("accession", flat=True).distinct()
    return [acc for acc in qs if acc]


def get_distinct_peptide_descriptions(reference=None):
    """
    Helper method to get distinct gene symbols.
    This method can be called from anywhere.
    """
    queryset = models.Peptide.objects.distinct("description").values("description")
    if reference:
        queryset = queryset.filter(replicon__reference__accession=reference)
    return [item["description"] for item in queryset]


def parse_default_data(value):
    # Convert "None", "null", or empty strings to Python None
    if value in {"None", "null", ""}:
        return None
    return value
