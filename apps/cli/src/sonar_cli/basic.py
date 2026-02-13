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

import datetime
import re
import sys
from typing import Dict
from typing import List
from typing import Optional

from sonar_cli.api_interface import APIClient
from sonar_cli.config import BASE_URL

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
        "IN": "in",  # not support
        "LIKE": "contains",  # not support
        "BETWEEN": "range",  # not support
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


def create_profile_query(profiles=[]):
    final_result = {}
    _temp_result = {}
    # create filter with level(depth)
    for _index, profile_set in enumerate(profiles):
        and_filter = {
            "andFilter": [
                {
                    "label": "DNA/AA Profile",
                    "value": ",".join(profile for profile in profile_set),
                }
            ]
        }
        _temp_result[_index] = and_filter
    # convert to final result.
    final_result = convert_to_desired_structure(_temp_result, 0)
    return final_result


def convert_to_desired_structure(result, depth=0):
    """
    Recursively constructs a nested filter structure by reversing the hierarchy from bottom to top.

    Parameters:
    - result (dict): A dictionary containing three levels (keys: 0-2), representing a hierarchical filter structure.
    - depth (int): The depth level to start the construction from. Defaults to 0.

    Returns:
    dict: A dictionary representing the transformed filter structure with combined "orFilter" values based on the depth.

    Example:
    --------
    Input: --profile
    result = {
        0: {'andFilter': [{'label': 'SNP AA', 'alt_aa': 'K', 'ref_aa': 'E', 'ref_pos': '484', 'protein_symbol': 'S'},
                          {'label': 'SNP AA', 'alt_aa': 'Y', 'ref_aa': 'N', 'ref_pos': '501', 'protein_symbol': 'S'}]},
        1: {'andFilter': [{'label': 'SNP Nt', 'alt_nuc': 'N', 'ref_nuc': 'A', 'ref_pos': '11022'}]},
        2: {'andFilter': [{'label': 'Del AA', 'first_deleted': '3001', 'last_deleted': '3004', 'protein_symbol': 'ORF1ab'},
                          {'label': 'Del Nt', 'first_deleted': '11288', 'last_deleted': '11300'}]}
    }

    converted_result = convert_to_desired_structure(result,0)

    Output:
    {"andFilter": [{"label": "SNP AA", "alt_aa": "K", "ref_aa": "E", "ref_pos": "484", "protein_symbol": "S"},
                   {"label": "SNP AA", "alt_aa": "Y", "ref_aa": "N", "ref_pos": "501", "protein_symbol": "S"}],
     "orFilter": [{"andFilter": [{"label": "SNP Nt", "alt_nuc": "N", "ref_nuc": "A", "ref_pos": "11022"}],
                   "orFilter": [{"andFilter": [{"label": "Del AA", "first_deleted": "3001", "last_deleted": "3004",
                                                 "protein_symbol": "ORF1ab"},
                                                {"label": "Del Nt", "first_deleted": "11288", "last_deleted": "11300"}],
                                 "orFilter": []}]}]}
    """
    final_result = {"andFilter": [], "orFilter": []}
    if depth not in result:
        return []

    current_level = result[depth]
    final_result["andFilter"] = current_level.get("andFilter", [])
    _result = convert_to_desired_structure(result=result, depth=depth + 1)
    if _result:
        final_result["orFilter"].append(_result)

    return final_result


def create_sample_query(samples: List):
    """
    Create a query object for samples.

    Parameters:
    - samples (List): A list of samples to be included in the query.

    Returns:
    - dict: A dictionary representing the query object with the following structure:
        {
            "label": "Sample",
            "exclude": False,
            "value": <list of samples>
        }

    NOTE:
    1. Currently, we do not support all exclusion operators, so 'exclude' is fixed with False.
    2. At the backend side, it will use the IN operator to match the samples.
    """
    _query = {"label": "Sample", "exclude": False, "value": samples}

    return _query


def get_operator(op: Optional[str] = None, inverse: bool = False) -> str:
    """Returns the appropriate operator for a given operation type and inversion flag.

    Args:
        op (Optional[str]): The operation to be performed. If not specified or empty, the default operation '=' will be used.
        inverse (bool, optional): A flag indicating whether to use the inverse of the operation. Defaults to False.

    Returns:
        str: The operator corresponding to the operation type and inversion flag.
    """
    op = op if op else OPERATORS["default"]
    return OPERATORS["standard"][op]
    # return OPERATORS["inverse"][op] if inverse else OPERATORS["standard"][op]


def create_annotaiton_query(
    annotation_type: List[str] = [],
    annotation_impact: List[str] = [],
):
    _query = {"andFilter": []}
    if annotation_type:
        _tmp_query = {
            "label": "Annotation",
            "property_name": "seq_ontology",
            "filter_type": "in",
            "value": annotation_type,
            "exclude": False,
        }
        _query["andFilter"].append(_tmp_query)
    if annotation_impact:
        _tmp_query = {
            "label": "Annotation",
            "property_name": "impact",
            "filter_type": "in",
            "value": annotation_impact,
            "exclude": False,
        }
        _query["andFilter"].append(_tmp_query)

    return _query


def construct_query(  # noqa: C901
    properties: Optional[Dict[str, List[str]]] = None,
    profiles: Optional[Dict[str, List[str]]] = None,
    defined_props: Optional[List[Dict[str, str]]] = [],
    with_sublineage: bool = False,
    samples: Optional[List[str]] = [],
    annotation_type: List[str] = [],
    annotation_impact: List[str] = [],
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
    LOGGER.debug(f"Input Samples:{samples}")
    LOGGER.debug(f"Input Profiles:{profiles}")
    LOGGER.debug(f"Input Properties:{properties}")
    LOGGER.debug(f"Enable Sublineage:{with_sublineage}")
    LOGGER.debug(f"Input Annotation Impact:{annotation_impact}")
    LOGGER.debug(f"Input Annotation Type:{annotation_type}")

    if samples:
        final_query["andFilter"].append(create_sample_query(samples))

    if profiles:
        final_query["andFilter"].append(create_profile_query(profiles))

    if annotation_type or annotation_impact:
        final_query["andFilter"].append(
            create_annotaiton_query(annotation_type, annotation_impact)
        )

    if properties:
        if defined_props:
            defined_props_dict = {
                item["name"]: item["query_type"] for item in defined_props
            }
        else:
            defined_props_dict = {}

        # combine AND with different prop_name
        _prop_query = {"andFilter": []}
        for prop_name, prop_value_list in properties.items():
            if prop_value_list is None:
                continue

            prop_type = defined_props_dict.get(prop_name, "value_varchar")
            LOGGER.debug(
                f"Process --> TYPE: {prop_type} NAME: {prop_name} VALUE: {prop_value_list}"
            )

            # NOTE: we dont use IN operator, so right now we combine them with OR, this can cause the performance issue.
            # TODO: conside to rewirte the code to use IN if possible.
            # combine OR
            _tmp_query = {"orFilter": []}
            for prop_value in prop_value_list:
                match = None
                # Determine the operation key and strip the inverse symbol if necessary
                negate = True if prop_value.startswith(NEGATE_OPERATOR) else False

                # check property query with the data type
                # not sure for two below
                # if prop_type == "value_text":
                #     pass
                # if prop_type == "value_zip":
                #     pass
                if (
                    prop_type == "value_varchar"
                    or prop_type == "value_zip"
                    or prop_type == "value_text"
                ):
                    extract_value = prop_value[1:] if negate else prop_value
                    if prop_name == "lineage":
                        _query = {
                            "label": "Lineages",
                            "lineageList": extract_value,
                            "exclude": negate,
                            "includeSublineages": with_sublineage,
                        }

                    else:
                        # Determine the operator
                        operator = get_operator(
                            (
                                "LIKE"
                                if extract_value.startswith("%")
                                or extract_value.endswith("%")
                                else "exact"
                            ),
                        )

                        _query = {
                            "label": "Property",
                            "property_name": prop_name,
                            "filter_type": operator,
                            "value": extract_value,
                            "exclude": negate,
                        }

                    match = True

                elif prop_type == "value_integer":
                    try:
                        if RANGE_OPERATOR not in prop_value:
                            match = int_pattern_single.match(prop_value)
                            operator = get_operator(
                                op=match.group(2), inverse=match.group(1)
                            )
                            extract_value = int(match.group(3))
                            _query = {
                                "label": "Property",
                                "property_name": prop_name,
                                "filter_type": operator,
                                "value": extract_value,
                                "exclude": negate,
                            }

                        else:  # Processing value range
                            match = int_pattern_range.match(prop_value)
                            num1 = int(match.group(2))
                            num2 = int(match.group(3))
                            operator = get_operator(
                                op="BETWEEN", inverse=match.group(1)
                            )
                            _query = {
                                "label": "Property",
                                "property_name": prop_name,
                                "filter_type": operator,
                                "value": [num1, num2],
                                "exclude": negate,
                            }
                    except (AttributeError, ValueError) as e:
                        LOGGER.error(
                            f"Error processing integer value: {prop_value} (input is not a valid type) - {str(e)}"
                        )
                        sys.exit(1)
                elif prop_type == "value_float":
                    try:
                        if RANGE_OPERATOR not in prop_value:
                            match = float_pattern_single.match(prop_value)
                            # Determine the operator
                            operator = get_operator(
                                op=match.group(2), inverse=match.group(1)
                            )
                            extract_value = float(match.group(3))
                            _query = {
                                "label": "Property",
                                "property_name": prop_name,
                                "filter_type": operator,
                                "value": extract_value,
                                "exclude": negate,
                            }

                            final_query["andFilter"].append(_query)
                        else:  # Processing value range
                            match = float_pattern_range.match(prop_value)

                            num1 = float(match.group(2))
                            num2 = float(match.group(3))
                            operator = get_operator(
                                op="BETWEEN", inverse=match.group(1)
                            )
                            _query = {
                                "label": "Property",
                                "property_name": prop_name,
                                "filter_type": operator,
                                "value": [num1, num2],
                                "exclude": negate,
                            }
                    except (AttributeError, ValueError) as e:
                        LOGGER.error(
                            f"Error processing float value: {prop_value} (input is not a valid type) - {str(e)}"
                        )
                        sys.exit(1)
                elif prop_type == "value_date":
                    try:
                        if RANGE_OPERATOR not in prop_value:
                            match = date_pattern_single.match(prop_value)
                            operator = get_operator(
                                op=match.group(2), inverse=match.group(1)
                            )
                            extract_value = match.group(3)
                            _query = {
                                "label": "Property",
                                "property_name": prop_name,
                                "filter_type": operator,
                                "value": match.group(3),
                                "exclude": negate,
                            }
                        else:  # Processing value range
                            match = date_pattern_range.match(prop_value)
                            operator = get_operator(
                                op="BETWEEN", inverse=match.group(1)
                            )
                            try:
                                date1 = datetime.datetime.strptime(
                                    match.group(2), "%Y-%m-%d"
                                )
                                date2 = datetime.datetime.strptime(
                                    match.group(3), "%Y-%m-%d"
                                )
                            except ValueError:
                                LOGGER.error("Invalid date format or out-of-range day.")
                                sys.exit(1)

                            # Plausibility check
                            if date1 >= date2:
                                LOGGER.error("Invalid range (" + match.group(0) + ").")
                                sys.exit(1)

                            _query = {
                                "label": "Property",
                                "property_name": prop_name,
                                "filter_type": operator,
                                "value": [match.group(2), match.group(3)],
                                "exclude": negate,
                            }
                    except (AttributeError, ValueError) as e:
                        LOGGER.error(
                            f"Error processing date value: {prop_value} (input is not a valid type) - {str(e)}"
                        )
                        sys.exit(1)
                else:
                    # fail to validate
                    LOGGER.error(
                        f"Fail to validate: {prop_name} - {prop_value} - {prop_type}"
                    )
                    sys.exit(1)

                if not match:
                    LOGGER.error(
                        f"Invalid format: the '{prop_name}' with its type '{prop_type}' and value '{prop_value}' is not in the expected format."
                    )
                    sys.exit(1)
                else:
                    _tmp_query["orFilter"].append(_query)
            if len(_tmp_query.get("orFilter", [])) > 0:
                _prop_query["andFilter"].append(_tmp_query)

    # Then merge back to the final query
    if len(_prop_query.get("andFilter", [])) > 0:
        final_query["andFilter"].append(_prop_query)

    # Traverse to add reference.
    # add_reference_query(final_query, reference_query=reference_query)
    # final_query = remove_empty_lists(final_query)
    return final_query


def add_reference_query(query_dict, reference_query):
    if isinstance(query_dict, dict):
        if "andFilter" in query_dict:
            for and_filter in query_dict["andFilter"]:
                # # If a filter with the same label is found, return without adding
                # if and_filter.get("label") == "Replicon":
                #     return
                add_reference_query(and_filter, reference_query)
            if query_dict["andFilter"]:
                query_dict["andFilter"].append(reference_query)


def remove_empty_lists(d):
    if isinstance(d, dict):
        return {
            k: remove_empty_lists(v)
            for k, v in d.items()
            if v and remove_empty_lists(v)
        }
    elif isinstance(d, list):
        return [remove_empty_lists(v) for v in d if v and remove_empty_lists(v)]
    else:
        return d


def _check_property(db=None, prop_name_list: list[str] = []):
    json_response = APIClient(base_url=BASE_URL).get_all_properties()
    # Use list to preserve order from API response
    available_names_list = [item["name"] for item in json_response["values"]]

    for k in prop_name_list:
        if k == "name":
            continue
        if k not in available_names_list:
            LOGGER.error(
                f"Key '{k}' not found in database, please check the typo or add it (add-prop) or list all properties (list-prop)."
            )
            sys.exit(1)
    first = "name"
    special_last = [
        "genomic_profiles",
        "proteomic_profiles",
        "init_upload_date",
        "last_update_date",
    ]
    # Remove these keys from their current positions while preserving order
    remaining_names = [
        name
        for name in available_names_list
        if name not in special_last and name != first
    ]
    # Build the final list
    final_order = [first] + remaining_names + special_last
    return final_order


def _check_reference(db=None, reference=None):
    base_url = db if db else BASE_URL
    accession_list = APIClient(base_url=base_url).get_all_references()

    # Create a mapping of IDs and accessions
    id_to_accession = {str(entry["id"]): entry["accession"] for entry in accession_list}
    accession_set = {entry["accession"] for entry in accession_list}

    if reference is not None:
        # Map ID to accession
        if reference in id_to_accession:
            reference = id_to_accession[reference]
            LOGGER.info(f"The reference {reference} is used.")
        elif reference not in accession_set:
            LOGGER.error(f"Check reference: The reference {reference} does not exist.")
            sys.exit(1)
        # else reference is valid accession, no need to change it
    return reference


def _log_import_mode(update: bool, quiet: bool):
    """Log the current import mode."""
    if not quiet:
        LOGGER.info(
            "Import mode: add/update existing samples in the database and cache directory."
            if update
            else "Import mode: skip existing samples in the database and cache directory."
        )


def _is_import_required(
    nextclade_json: List[str],
    fasta: List[str],
    tsv_files: List[str],
    csv_files: List[str],
    update: bool,
) -> bool:
    """Check if import is required."""
    if not fasta and not nextclade_json:
        if tsv_files or csv_files or update:
            return True
        else:
            return False
    return True
