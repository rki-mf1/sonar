# all functions that have built for sonar-cli

#
"""
CharField:
exact
iexact
contains
icontains
startswith
endswith
istartswith
iendswith

IntegerField, FloatField, DecimalField:
exact
gt (greater than)
lt (less than)
gte (greater than or equal to)
lte (less than or equal to)
DateField, DateTimeField:

exact
gt
lt
gte
lte
year
month
day

BooleanField:
exact
"""


#

import pprint
import re
import sys
from typing import Dict
from typing import List
from typing import Optional

from .logging import LoggingConfigurator


# Initialize logger
LOGGER = LoggingConfigurator.get_logger()

NEGATE_OPERATOR = "^"
RANGE_OPERATOR = ":"

OPERATORS = {
    "standard": {
        "exact": "exact",
        ">": "gt",
        "<": "lt",
        ">=": "gte",
        "<=": "lte",
        "IN": "IN",  # not support
        "LIKE": "LIKE",  # not support
        "BETWEEN": "BETWEEN",  # not support
    },
    "inverse": {  # not support
        "exact": "iexact",
        "contains": "icontains",
        "lt": "gte",
        "gte": "lt",
        "gt": "lte",
        "lte": "gt",
    },
    "default": "exact",
}

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

dna_allowed_letters = "[" + "".join(IUPAC_CODES["nt"].keys()) + "]"


regexes = {
    "snv": re.compile(r"^(|[^:]+:)?([^:]+:)?([A-Z]+)([0-9]+)(=?[A-Zxn]+)$"),
    "del": re.compile(r"^(|[^:]+:)?([^:]+:)?del:(=?[0-9]+)(|-=?[0-9]+)?$"),
}
# print(match.group(0)) whole match
# print(match.group(1))
# print(match.group(2)) gene name
# print(match.group(3)) Ref
# print(match.group(4)) Postion
# print(match.group(5)) Alt


def create_profile_query(mutation):  # noqa: C901
    """
    # check profile
    """
    _query = {"label": ""}
    for mutation_type, regex in regexes.items():
        match = regex.match(mutation)
        if match:

            if match.group(2):
                gene_name = match.group(2)[:-1]
            else:
                gene_name = None

            if mutation_type == "snv":

                alt = match.group(5)

                for x in alt:
                    if x not in IUPAC_CODES["aa"]:
                        LOGGER.error(f"Invalid alternate allele notation '{alt}'.")
                        sys.exit(1)
                # AA
                if gene_name is not None:
                    _query["alt_aa"] = alt
                    _query["ref_aa"] = match.group(3)
                    _query["ref_pos"] = match.group(4)

                    _query["protein_symbol"] = gene_name
                    if len(alt) == 1:  # SNP AA
                        _query["label"] = "SNP AA"
                    else:  # Ins AA
                        _query["label"] = "Ins AA"
                else:
                    _query["alt_nuc"] = alt
                    _query["ref_nuc"] = match.group(3)
                    _query["ref_pos"] = match.group(4)

                    if len(alt) == 1:  # SNP Nt
                        _query["label"] = "SNP Nt"
                    else:  # Ins Nt
                        _query["label"] = "Ins Nt"

            elif mutation_type == "del":
                _query["first_delete"] = match.group(3)
                _query["last_detete"] = match.group(4)[1:]

                if gene_name is not None:  # Del AA
                    _query["protein_symbol"] = gene_name
                    _query["label"] = "Del AA"
                else:  # Del Nt
                    _query["label"] = "Del Nt"
        else:
            # fail to validate
            pass
    return _query


def create_property_query(prop_name, prop_value):
    """
    # check property

    # do we really need to know data type?

    """
    _query = {"label": "Property", "property_name": prop_name, "value": prop_value}

    return _query


def construct_query(  # noqa: C901
    properties: Optional[Dict[str, List[str]]] = None,
    profiles: Optional[Dict[str, List[str]]] = None,
    defined_props: Optional[List[Dict[str, str]]] = [],
):

    int_pattern_single = re.compile(r"^(\^*)((?:>|>=|<|<=|!=|=)?)(-?[1-9]+[0-9]*)$")
    int_pattern_range = re.compile(r"^(\^*)(-?[1-9]+[0-9]*):(-?[1-9]+[0-9]*)$")
    date_pattern_single = re.compile(
        r"^(\^*)((?:>|>=|<|<=|!=|=)?)([0-9]{4}-[0-9]{2}-[0-9]{2})$"
    )
    date_pattern_range = re.compile(
        r"^(\^*)([0-9]{4}-[0-9]{2}-[0-9]{2}):([0-9]{4}-[0-9]{2}-[0-9]{2})$"
    )
    float_pattern_single = re.compile(
        r"^(\^*)((?:>|>=|<|<=|!=|=)?)(-?[1-9]+[0-9]*(?:.[0-9]+)*)$"
    )
    float_pattern_range = re.compile(
        r"^(\^*)(-?[1-9]+[0-9]*(?:.[0-9]+)*):(-?[1-9]+[0-9]*(?:.[0-9]+)*)$"
    )

    final_query = {"andFilter": [], "orFilter": []}
    print("Input Profiles:", profiles)

    if defined_props:
        defined_props_dict = {
            item["name"]: item["query_type"] for item in defined_props
        }
    else:
        defined_props_dict = {}

    # combine OR
    profile_OR_query = {"orFilter": []}
    for profile_set in profiles:

        # combine AND
        profile_AND_query = {"andFilter": []}
        for mutation in profile_set:
            _query = create_profile_query(mutation)
            profile_AND_query["andFilter"].append(_query)
        profile_OR_query["orFilter"].append(profile_AND_query)

    final_query["andFilter"].append(profile_OR_query)

    # combine AND

    for prop_name, prop_value_list in properties.items():

        if prop_value_list is None:
            continue
        prop_type = defined_props_dict.get(prop_name, "value_varchar")
        print(
            f"Process --> TYPE: {prop_type} NAME: {prop_name} VALUE: {prop_value_list}"
        )

        for prop_value in prop_value_list:

            # check property query with the data type
            if prop_type == "value_varchar":
                # Determine the operation key and strip the inverse symbol if necessary
                negate = True if prop_value.startswith(NEGATE_OPERATOR) else False
                extract_value = prop_value[1:] if negate else prop_value
                # Determine the operator
                operator = get_operator(
                    "LIKE"
                    if extract_value.startswith("%") or extract_value.endswith("%")
                    else "exact",
                    negate,
                )

                final_query["andFilter"].append(
                    {
                        "label": "Property",
                        "property_name": prop_name,
                        "filter_type": operator,
                        "value": extract_value,
                    }
                )

            elif prop_type == "value_integer":

                if RANGE_OPERATOR not in prop_value:
                    match = int_pattern_single.match(prop_value)
                    # Determine the operator
                    operator = get_operator(op=match.group(2), inverse=match.group(1))
                    extract_value = int(match.group(3))
                    _query = {
                        "label": "Property",
                        "property_name": prop_name,
                        "filter_type": operator,
                        "value": extract_value,
                    }

                    final_query["andFilter"].append(_query)
                else:  # Processing value range
                    match = int_pattern_range.match(prop_value)

                    if not match:
                        LOGGER.error(
                            f"Invalid format: the '{prop_name}' with its type '{prop_type}' and value '{prop_value}' is not in the expected format."
                        )
                        sys.exit(1)

                    int(match.group(2))
                    int(match.group(3))

            # TODO: check float format.
            elif prop_type == "value_float":

                if RANGE_OPERATOR not in prop_value:
                    match = float_pattern_single.match(prop_value)
                    # Determine the operator
                    operator = get_operator(op=match.group(2), inverse=match.group(1))
                    extract_value = int(match.group(3))
                    _query = {
                        "label": "Property",
                        "property_name": prop_name,
                        "filter_type": operator,
                        "value": extract_value,
                    }

                    final_query["andFilter"].append(_query)
                else:  # Processing value range
                    match = float_pattern_range.match(prop_value)

                    if not match:
                        LOGGER.error(
                            f"Invalid format: the '{prop_name}' with its type '{prop_type}' and value '{prop_value}' is not in the expected format."
                        )
                        sys.exit(1)

                    int(match.group(2))
                    int(match.group(3))
            # TODO: check date format.
            elif prop_type == "value_date":
                if RANGE_OPERATOR not in prop_value:
                    match = date_pattern_single.match(prop_value)
                else:  # Processing value range
                    match = date_pattern_range.match(prop_value)

    pprint.pprint(final_query, width=1)

    return final_query


def get_operator(op: Optional[str] = None, inverse: bool = False) -> str:
    """Returns the appropriate operator for a given operation type and inversion flag.

    Args:
        op (Optional[str]): The operation to be performed. If not specified or empty, the default operation '=' will be used.
        inverse (bool, optional): A flag indicating whether to use the inverse of the operation. Defaults to False.

    Returns:
        str: The operator corresponding to the operation type and inversion flag.
    """
    op = op if op else OPERATORS["default"]
    return OPERATORS["inverse"][op] if inverse else OPERATORS["standard"][op]
