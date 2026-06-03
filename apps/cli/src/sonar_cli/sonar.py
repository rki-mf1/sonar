import argparse
from datetime import datetime
import sys
from typing import Optional

from sonar_cli import config
from sonar_cli.common_utils import combine_sample_argument
from sonar_cli.common_utils import convert_default
from sonar_cli.logging import LoggingConfigurator
from sonar_cli.utils import sonarUtils
from sonar_cli.utils1 import sonarUtils1
from tabulate import tabulate

from . import DESCRIPTION
from . import get_version
from . import NAME

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()


class args_namespace(object):
    """An empty class for storing command-line
    arguments as object attributes."""

    pass


def parse_args(args=None):
    """
    Parse command-line arguments using argparse.ArgumentParser.

    Args:
        args (list): List of command-line arguments. Default is None.
        namespace (argparse.Namespace): An existing namespace to populate with parsed arguments.
        Default is None.

    Returns:
        argparse.Namespace: Namespace containing parsed command-line arguments.
    """
    version = get_version()
    parser = argparse.ArgumentParser(
        prog="sonar-cli",
        description=f"{NAME} {version}: {DESCRIPTION}",
    )
    general_parser = create_parser_general()
    database_parser = create_parser_database()
    output_parser = create_parser_output()
    sample_parser = create_parser_sample()
    sequence_parser = create_parser_sequence()
    property_parser = create_parser_property()
    reference_parser = create_parser_reference()
    thread_parser = create_parser_thread()
    lineage_parser = create_parser_lineage()
    resource_subparsers = parser.add_subparsers(dest="resource", required=True)

    reference_parser_root = resource_subparsers.add_parser(
        "reference", help="Manage reference genomes in the database."
    )
    reference_subparsers = reference_parser_root.add_subparsers(
        dest="verb", required=True
    )
    reference_subparsers, _ = create_subparser_list_reference(
        reference_subparsers, database_parser, general_parser
    )
    reference_subparsers, _ = create_subparser_add_reference(
        reference_subparsers, database_parser, general_parser
    )
    reference_subparsers, _ = create_subparser_delete_reference(
        reference_subparsers, database_parser, reference_parser, general_parser
    )

    property_parser_root = resource_subparsers.add_parser(
        "property", help="Manage queryable properties in the database."
    )
    property_subparsers = property_parser_root.add_subparsers(
        dest="verb", required=True
    )
    property_subparsers, _ = create_subparser_list_prop(
        property_subparsers, database_parser, general_parser
    )
    property_subparsers, _ = create_subparser_add_prop(
        property_subparsers, database_parser, property_parser, general_parser
    )
    property_subparsers, _ = create_subparser_delete_prop(
        property_subparsers, database_parser, property_parser, general_parser
    )

    sample_parser_root = resource_subparsers.add_parser(
        "sample", help="Import, match, and delete samples."
    )
    sample_subparsers = sample_parser_root.add_subparsers(dest="verb", required=True)
    sample_subparsers, _ = create_subparser_import(
        sample_subparsers,
        database_parser,
        thread_parser,
        reference_parser,
        general_parser,
    )
    sample_subparsers, subparser_match = create_subparser_match(
        sample_subparsers,
        database_parser,
        reference_parser,
        sample_parser,
        output_parser,
        general_parser,
    )
    sample_subparsers, _ = create_subparser_delete_sample(
        sample_subparsers, database_parser, sample_parser, general_parser
    )

    sequence_parser_root = resource_subparsers.add_parser(
        "sequence", help="Delete sequences from the database."
    )
    sequence_subparsers = sequence_parser_root.add_subparsers(
        dest="verb", required=True
    )
    sequence_subparsers, _ = create_subparser_delete_sequence(
        sequence_subparsers, database_parser, sequence_parser, general_parser
    )

    dataset_parser_root = resource_subparsers.add_parser(
        "dataset", help="Download and import public datasets."
    )
    dataset_subparsers = dataset_parser_root.add_subparsers(dest="verb", required=True)
    dataset_subparsers, _ = create_subparser_import_dataset(
        dataset_subparsers,
        database_parser,
        thread_parser,
        reference_parser,
        general_parser,
    )

    lineage_parser_root = resource_subparsers.add_parser(
        "lineage", help="Import lineage parent-child relationships."
    )
    lineage_subparsers = lineage_parser_root.add_subparsers(dest="verb", required=True)
    lineage_subparsers, _ = create_subparser_lineage_import(
        lineage_subparsers, lineage_parser, output_parser, general_parser
    )

    task_parser_root = resource_subparsers.add_parser(
        "task", help="Query background job status."
    )
    task_subparsers = task_parser_root.add_subparsers(dest="verb", required=True)
    task_subparsers, _ = create_subparser_tasks(
        task_subparsers, database_parser, general_parser
    )

    info_parser_root = resource_subparsers.add_parser(
        "info", help="Display database information and statistics."
    )
    info_subparsers = info_parser_root.add_subparsers(dest="verb", required=True)
    info_subparsers, _ = create_subparser_info(
        info_subparsers, database_parser, general_parser
    )
    # version parser
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{NAME} {version}",
        help="Show program's version number and exit.",
    )

    # register known arguments
    # add database-specific properties to match subparser
    user_namespace = args_namespace()
    known_args, _ = parser.parse_known_args(args=args, namespace=user_namespace)
    if is_match_selected(known_args):
        _, values_listofdict = sonarUtils.get_all_properties()
        for property in values_listofdict:
            subparser_match.add_argument(
                "--" + property["name"],
                type=str,
                # action="append",  --> this will create a complex query (doesnt support it for now.)
                nargs="+",
            )

    return parser.parse_args(args=args, namespace=user_namespace)


def is_match_selected(namespace: Optional[argparse.Namespace] = None) -> bool:
    """
    Checks if the 'match' command is selected and the 'db' attribute is present in the arguments.

    Args:
        namespace: Namespace object for storing argument values (default: None)

    Returns:
        True if 'match' command is selected and 'db' attribute is present, False otherwise
    """
    return (
        getattr(namespace, "resource", None) == "sample"
        and getattr(namespace, "verb", None) == "match"
    )


def create_parser_lineage() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-p",
        "--pathogen",
        metavar="STR",
        help="Select a pathogen. (choices: %(choices)s. default: %(default)s)",
        type=str,
        choices=["SARS-CoV-2", "Influenza", "RSV"],
        default="SARS-CoV-2",
    )
    parser.add_argument(
        "-l",
        "--lineage",
        metavar="STR",
        help="If a lineage file is provided, this given file will be used instead of downloading the latest lineage file.",
        type=str,
        required=False,
    )
    return parser


def create_parser_general() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--verbose",
        help="Increase the amount of logging messages show in the console",
        action="store_true",
    )
    return parser


def create_parser_reference() -> argparse.ArgumentParser:
    """Creates a 'reference' parent parser with common arguments and
    options for the command-line interface.

    Returns:
        argparse.ArgumentParser: The created 'reference' parent parser.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-r",
        "--reference",
        metavar="STR",
        help="reference accession",
        type=str,
        required=True,
    )
    return parser


def create_subparser_info(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "show",
        parents=parent_parsers,
        help="Display database information and statistics.",
    )

    return subparsers, parser


def create_subparser_delete_reference(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    # Delete Reference.
    parser = subparsers.add_parser(
        "delete",
        parents=parent_parsers,
        help="Deletes a reference from the database.",
    )
    parser.add_argument(
        "--force",
        help="skip user confirmation.",
        action="store_true",
    )
    return subparsers, parser


def create_subparser_delete_sample(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    """
    Creates an 'delete_sample' subparser with command-specific arguments and options for the command-line interface.

    Args:
        subparsers (argparse._SubParsersAction): ArgumentParser object to attach the 'delete' subparser to.
        parent_parsers (argparse.ArgumentParser): ArgumentParser objects providing common arguments and options.

    Returns:
        argparse.ArgumentParser: The created 'delete_sample' subparser.
    """
    parser_delete_sample = subparsers.add_parser(
        "delete",
        help="Deletes samples from the database",
        parents=parent_parsers,
    )
    parser_delete_sample.add_argument(
        "--force",
        help="skip user confirmation.",
        action="store_true",
    )

    return subparsers, parser_delete_sample


def create_subparser_delete_sequence(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    """
    Creates an 'delete' subparser with command-specific arguments and options for the command-line interface.

    Args:
        subparsers (argparse._SubParsersAction): ArgumentParser object to attach the 'delete' subparser to.
        parent_parsers (argparse.ArgumentParser): ArgumentParser objects providing common arguments and options.

    Returns:
        argparse.ArgumentParser: The created 'delete_sequence' subparser.
    """
    parser_delete_sequence = subparsers.add_parser(
        "delete",
        help="Deletes sequences from the database",
        parents=parent_parsers,
    )
    parser_delete_sequence.add_argument(
        "--force",
        help="skip user confirmation.",
        action="store_true",
    )

    return subparsers, parser_delete_sequence


def create_parser_database() -> argparse.ArgumentParser:
    """Creates a 'database' parent parser with common arguments and options for the command-line interface.

    Returns:
        argparse.ArgumentParser: The created 'database' parent parser.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--db",
        metavar="URL",
        help="URL to backend (example http://127.0.0.1:8000/)",
        type=str,
    )
    return parser


def create_parser_output() -> argparse.ArgumentParser:
    """Creates an 'output' parent parser with common arguments and options for the command-line interface.

    Returns:
        argparse.ArgumentParser: The created 'output' parent parser.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-o",
        "--out",
        metavar="FILE",
        help="write output file (existing files will be overwritten!)",
        type=str,
        default=None,
    )
    return parser


def create_parser_sample() -> argparse.ArgumentParser:
    """Creates a 'sample' parent parser with common arguments and options for the command-line interface.

    Returns:
        argparse.ArgumentParser: The created 'sample' parent parser.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--sample",
        metavar="STR",
        help="sample accession(s) to consider",
        type=str,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--sample-file",
        metavar="FILE",
        help="file containing sample accession(s) to consider (one per line)",
        type=str,
        nargs="+",
        default=[],
    )
    return parser


def create_parser_sequence() -> argparse.ArgumentParser:
    """Creates a 'sample' parent parser with common arguments and options for the command-line interface.

    Returns:
        argparse.ArgumentParser: The created 'sample' parent parser.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--sequence",
        metavar="STR",
        help="sequence accession(s) to consider",
        type=str,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--sequence-file",
        metavar="FILE",
        help="file containing sequence accession(s) to consider (one per line)",
        type=str,
        nargs="+",
        default=[],
    )
    return parser


def create_parser_property() -> argparse.ArgumentParser:
    """Creates a 'property' parent parser with common arguments and options for the command-line interface.

    Returns:
        argparse.ArgumentParser: The created 'property' parent parser.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--name", metavar="STR", help="property name", type=str, required=True
    )
    return parser


def create_parser_thread() -> argparse.ArgumentParser:
    """Creates a 'thread' parent parser with common arguments and options
    for the command-line interface.

    Returns:
        argparse.ArgumentParser: The created 'thread' parent parser.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-t",
        "--threads",
        metavar="INT",
        help="number of threads to use (default: %(default)s)",
        type=int,
        default=1,
    )
    return parser


def create_subparser_tasks(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    list_parser = subparsers.add_parser(
        "list",
        parents=parent_parsers,
        help="List all known background jobs.",
    )

    show_parser = subparsers.add_parser(
        "show",
        parents=parent_parsers,
        help="Show the status of a specific background job.",
    )
    show_parser.add_argument(
        "--jobid", help="Search for a specific job ID", type=str, required=True
    )

    watch_parser = subparsers.add_parser(
        "watch",
        parents=parent_parsers,
        help="Run background checks periodically for the specified job.",
    )
    watch_parser.add_argument(
        "--jobid", help="Search for a specific job ID", type=str, required=True
    )
    watch_parser.add_argument(
        "--interval",
        help="Interval in seconds to check the job status (default: %(default)s)",
        type=int,
        default=60,
    )
    return subparsers, list_parser


def create_subparser_list_prop(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    """
    Creates the 'property list' subparser with command-specific arguments and options for the command-line interface.

    Args:
        subparsers (argparse._SubParsersAction): ArgumentParser object to attach the 'list' subparser to.
        parent_parsers (argparse.ArgumentParser): ArgumentParser objects providing common arguments and options.

    Returns:
        argparse.ArgumentParser: The created 'property list' subparser.
    """
    parser = subparsers.add_parser(
        "list",
        help="Lists all sample properties added to the database",
        parents=parent_parsers,
    )
    return subparsers, parser


def create_subparser_list_reference(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    # View Reference.
    parser = subparsers.add_parser(
        "list",
        parents=parent_parsers,
        help="Lists all available references in the database",
    )
    return subparsers, parser


def create_subparser_lineage_import(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "import",
        parents=parent_parsers,
        help="Perform lineage import to the database",
    )
    return subparsers, parser


def create_subparser_import_dataset(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    """
    Creates the 'dataset import' subparser for downloading and importing public datasets.

    Args:
        subparsers (argparse._SubParsersAction): ArgumentParser object to attach the subparser to.
        parent_parsers (argparse.ArgumentParser): ArgumentParser objects providing common arguments.

    Returns:
        argparse.ArgumentParser: The created 'dataset import' subparser.
    """
    parser = subparsers.add_parser(
        "import",
        parents=parent_parsers,
        help="Download and import public pathogen genomics datasets",
        description=(
            "Download and import public pathogen genomics datasets from various sources. "
            "Supported sources: rki (RKI SARS-CoV-2 from Germany), pathoplexus (various pathogens)."
        ),
    )

    parser.add_argument(
        "-s",
        "--source",
        metavar="STR",
        help="Data source (choices: %(choices)s)",
        type=str,
        choices=["rki", "pathoplexus"],
        required=True,
    )
    parser.add_argument(
        "-p",
        "--pathogen",
        metavar="STR",
        help=(
            "Pathogen name. For RKI: sars-cov-2. "
            "For Pathoplexus: sars-cov-2, rsv-a, rsv-b, mpox, hmpv, marburg, measles, "
            "ebola-zaire, ebola-sudan, west-nile"
        ),
        type=str,
        required=True,
    )
    parser.add_argument(
        "--sample-size",
        metavar="INT",
        help="Number of samples to import. If not specified, imports all samples.",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--method",
        help="Select alignment method (default: %(default)s)",
        choices=["mafft", "parasail", "wfa"],
        type=str,
        default="mafft",
    )
    parser.add_argument(
        "--cache",
        metavar="DIR",
        help="Directory for caching downloaded data (default: a temporary directory is created)",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--no-progress",
        help="Don't show progress bars while downloading/importing",
        action="store_true",
    )
    parser.add_argument(
        "--download-only",
        help="Only download and preprocess data, do not import into database",
        action="store_true",
    )
    parser.add_argument(
        "--auto-link",
        help="Automatically link TSV columns with database fields based on identical names",
        action="store_true",
    )
    parser.add_argument(
        "--skip-nx",
        help="Exclude mutations containing N or X from being imported",
        action="store_true",
    )
    parser.add_argument(
        "--cols",
        help="assign column names used in the provided TSV/CSV file to the matching property names provided by the database in the form PROP=COL (e.g. name=GenomeID)",
        type=str,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--auto-anno",
        help="automatically annotate sample with SnpEff tool.",
        action="store_true",
    )
    parser.add_argument(
        "--debug",
        help="save additional files to the cache dir that can be useful when debugging errors",
        action="store_true",
    )
    parser.add_argument(
        "--must-pass-paranoid",
        help="abort import if any sequence fails the 'paranoid' test",
        action="store_true",
    )
    parser.add_argument(
        "--no-skip",
        help="use '--no-skip' to not skip samples already existing in the database (default: (skip))",
        action="store_true",
    )
    return subparsers, parser


def create_subparser_import(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    """
    Creates an 'import' subparser with command-specific arguments and options for the command-line interface.

    Args:
        subparsers (argparse._SubParsersAction): ArgumentParser object to attach the 'import' subparser to.
        parent_parsers (argparse.ArgumentParser): ArgumentParser objects providing common arguments and options.

    Returns:
        argparse.ArgumentParser: The created 'import' subparser.
    """
    parser = subparsers.add_parser(
        "import",
        help="Imports genome sequences and sample properties into the database.",
        parents=parent_parsers,
    )

    # help="Select alignment tools: mafft, parasail, wfa (default: %(default)s)",
    parser.add_argument(
        "--method",
        help="select alignment method (default: %(default)s)",
        choices=["mafft", "parasail", "wfa"],
        type=str,
        default="mafft",
    )
    parser.add_argument(
        "--nextclade-json",
        help="output from nextclade tool (e.g. nextclade.json)",
        type=str,
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "--fasta",
        help="fasta file containing genome sequences to import",
        type=str,
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "--tsv",
        metavar="TSV_FILE",
        help="tab-delimited file containing sample properties to import",
        type=str,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--csv",
        metavar="CSV_FILE",
        help="comma-delimited file containing sample properties to import",
        type=str,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--cols",
        help="assign column names used in the provided TSV/CSV file to the matching property names provided by the database in the form PROP=COL (e.g. name=GenomeID)",
        type=str,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--auto-link",
        help="automatically link TSV/CSV columns with database fields based on identical names",
        action="store_true",
    )
    parser.add_argument(
        "--auto-anno",
        help="automatically annotate sample with SnpEff tool.",
        action="store_true",
    )
    parser.add_argument(
        "--no-skip",
        help="use '--no-skip' to not skip samples already existing in the database (default: (skip))",
        action="store_true",
    )
    parser.add_argument(
        "--cache",
        metavar="DIR",
        help="directory for chaching data (default: a temporary directory is created)",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--no-progress",
        help="don't show progress bars while importing",
        action="store_true",
    )
    parser.add_argument(
        "--no-upload",
        help="don't upload processed sample to sonar-backend",
        action="store_true",
    )
    parser.add_argument(
        "--skip-nx",
        help="exclude mutations containing N or X from being imported into the database (default; sonar includes mutations containing 'N' or 'X' when importing).",
        action="store_true",
    )
    parser.add_argument(
        "--debug",
        help="save additional files to the cache dir that can be useful when debugging errors",
        action="store_true",
    )
    parser.add_argument(
        "--must-pass-paranoid",
        help="abort import if any sequence fails the 'paranoid' test",
        action="store_true",
    )
    return subparsers, parser


def create_subparser_add_reference(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "add",
        parents=parent_parsers,
        help="Adds reference genome to the database.",
    )
    parser.add_argument(
        "--genbank",
        metavar="FILE",
        help=(
            "GenBank file(s) of a reference genome. Normally, one GenBank file per one reference genome, "
            "however, in a case of a segmented genome (multiple genbank files), user can provide multiple files. "
            "For example, --genbank InfluenzaA_H1N1_seg1.gb InfluenzaA_H1N1_seg2.gb InfluenzaA_H1N1_seg7.gb "
            "or --genbank InfluenzaA_H1N1_seg1.gb --genbank InfluenzaA_H1N1_seg2.gb. "
            "This will automatically treat this import as a segmented genome, and the first file will be used as the "
            "index in the reference table and shown information in the reference list command."
        ),
        type=str,
        action="extend",
        nargs="+",
        default=[],
        required=True,
    )

    return subparsers, parser


def create_subparser_add_prop(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    """
    Creates the 'property add' subparser with command-specific arguments and options for the command-line interface.

    Args:
        subparsers (argparse._SubParsersAction): ArgumentParser object to attach the 'add' subparser to.
        parent_parsers (argparse.ArgumentParser): ArgumentParser objects providing common arguments and options.

    Returns:
        argparse.ArgumentParser: The created 'property add' subparser.
    """
    parser = subparsers.add_parser(
        "add", help="add a property to the database", parents=parent_parsers
    )
    parser.add_argument(
        "--descr",
        metavar="STR",
        help="a short description of the property",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--dtype",
        metavar="STR",
        help="the data type of the property",
        type=str,
        choices=[
            "value_integer",
            "value_float",
            "value_text",
            "value_date",
            "value_zip",
            "value_varchar",
        ],
        required=True,
    )
    """
    parser.add_argument(
        "--qtype",
        metavar="STR",
        help="the query type of the property",
        type=str,
        choices=["numeric", "float", "text", "date", "zip", "pango"],
        default=None,
    )
    """
    parser.add_argument(
        "--default",
        metavar="VAR",
        help="the default value of the property (default: None)",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--subject",
        metavar="VAR",
        help="choose between sample or variant property (choices: %(choices)s, default: %(default)s)",
        choices=["sample", "variant"],
        default="sample",
    )

    return subparsers, parser


def create_subparser_delete_prop(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    """
    Creates the 'property delete' subparser with command-specific arguments and options for the command-line interface.

    Args:
        subparsers (argparse._SubParsersAction): ArgumentParser object to attach the 'delete' subparser to.
        parent_parsers (argparse.ArgumentParser): ArgumentParser objects providing common arguments and options.

    Returns:
        argparse.ArgumentParser: The created 'property delete' subparser.
    """
    parser = subparsers.add_parser(
        "delete", help="delete a property to the database", parents=parent_parsers
    )
    parser.add_argument(
        "--force",
        help="skip user confirmation.",
        action="store_true",
    )
    return subparsers, parser


def create_subparser_match(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    """
    Creates a 'match' subparser with command-specific arguments and options for the command-line interface.

    Args:
        subparsers (argparse._SubParsersAction): An ArgumentParser object to attach the 'match' subparser to.
        parent_parsers (argparse.ArgumentParser): A list of ArgumentParser objects providing common arguments and options.

    Returns:
        argparse.ArgumentParser: The created 'match' subparser.
    """
    parser = subparsers.add_parser(
        "match",
        help="Matches samples based on mutation profiles and/or properties.",
        parents=parent_parsers,
    )

    parser.add_argument(
        "--profile",
        "-p",
        metavar="STR",
        help="match genomes sharing the given mutation profile",
        type=str,
        action="append",
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--showNX",
        help="include non-informative polymorphisms in resulting mutation profiles (X for AA and N for NT)",
        action="store_true",
    )
    # parser.add_argument(
    #     "--frameshifts-only",
    #     help="match only mutation profiles with frameshift mutations",
    #     action="store_true",
    # )
    parser.add_argument(
        "--ex-anno",
        help="exclude annotation information in output",
        action="store_true",
    )
    parser.add_argument(
        "--with-sublineage",
        help="recursively get all sublineages from a given lineage (--lineage) (only child) ",
        action="store_true",
    )
    parser.add_argument(
        "--anno-impact",
        metavar="STR",
        help="filter by effect impact; HIGH, MODERATE, LOW, MODIFIER",
        type=str,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--anno-type",
        metavar="STR",
        help="filter by annotation (a.k.a. effect) using sequence ontology terms; frameshift_variant, missense_variant, synonymous_variant etc.",
        type=str,
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--out-cols",
        metavar="STR",
        help="define output columns for CSV and TSV files (by default all available columns are shown)",
        type=str,
        nargs="+",
        default=[],
    )
    mutually_exclusive_group = parser.add_mutually_exclusive_group()

    mutually_exclusive_group.add_argument(
        "--count", help="count matching genomes only", action="store_true"
    )
    mutually_exclusive_group.add_argument(
        "--format",
        help="output format (choices: %(choices)s. default: %(default)s)",
        choices=["csv", "tsv", "vcf"],
        default="tsv",
    )
    return subparsers, parser


def handle_import(args: argparse.Namespace):
    """
    Handle data import.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
    """

    if args.method == "mafft":
        LOGGER.info("Alignment Tool: MAFFT")
    elif args.method == "parasail":
        LOGGER.info("Alignment Tool: Parasail")
    elif args.method == "wfa":
        LOGGER.info("Alignment Tool: WFA2-lib")
    else:
        LOGGER.warning(
            "Invalid --method. Please use 'sample import -h' to see available methods"
        )
        exit(1)
    LOGGER.info(f"Skip N/X mutation: {args.skip_nx}")
    LOGGER.info(f"Variant Annotation: {args.auto_anno}")
    LOGGER.info(f"All sequences must pass 'paranoid' test: {args.must_pass_paranoid}")
    sonarUtils.import_data(
        db=args.db,
        nextclade_json=args.nextclade_json,
        fasta=args.fasta,
        csv_files=args.csv,
        tsv_files=args.tsv,
        prop_links=args.cols,
        cachedir=args.cache,
        autolink=args.auto_link,
        auto_anno=args.auto_anno,
        progress=not args.no_progress,
        update=args.no_skip,
        threads=args.threads,
        quiet=not args.verbose,
        reference=args.reference,
        method=args.method,
        no_upload_sample=args.no_upload,
        include_nx=not args.skip_nx,
        debug=args.debug,
        must_pass_paranoid=args.must_pass_paranoid,
    )


def handle_import_dataset(args: argparse.Namespace):
    """
    Handle downloading and importing public datasets.

    This function downloads data from public sources (RKI, Pathoplexus),
    preprocesses it, and optionally imports it into the sonar database.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
    """
    from sonar_cli.dataset_import import get_importer, SUPPORTED_PATHOGENS

    source = args.source.lower()
    pathogen = args.pathogen.lower()

    # Validate pathogen for the source
    if pathogen not in SUPPORTED_PATHOGENS.get(source, []):
        LOGGER.error(
            f"Pathogen '{pathogen}' is not supported for source '{source}'. "
            f"Supported pathogens: {SUPPORTED_PATHOGENS[source]}"
        )
        exit(1)

    try:
        # Create importer
        with get_importer(
            source=source,
            pathogen=pathogen,
            cache_dir=args.cache,
            sample_size=args.sample_size,
        ) as importer:
            # Download and preprocess
            fasta_path, tsv_path = importer.run()

            if args.download_only:
                LOGGER.info("Download-only mode: skipping database import")
                LOGGER.info(f"Files are ready at: {importer.cache_dir}")
                return

            # Import into database
            LOGGER.info("Importing data into database...")
            sonarUtils.import_data(
                db=args.db,
                nextclade_json=None,
                fasta=[str(fasta_path)],
                csv_files=[],
                tsv_files=[str(tsv_path)],
                prop_links=args.cols,
                cachedir=args.cache,
                autolink=args.auto_link,
                auto_anno=args.auto_anno,
                progress=not args.no_progress,
                update=args.no_skip,
                threads=args.threads,
                quiet=not args.verbose,
                reference=args.reference,
                method=args.method,
                no_upload_sample=False,
                include_nx=not args.skip_nx,
                debug=args.debug,
                must_pass_paranoid=args.must_pass_paranoid,
            )

            LOGGER.info("Dataset import completed successfully!")

    except Exception as e:
        LOGGER.error(f"Dataset import failed: {e}")
        raise


def handle_match(args: argparse.Namespace):
    """
    Handle profile and property matching.

    This function matches samples based on their properties and a given profile.
    The samples can be provided as command line arguments or within a file.
    The output can be customized by selecting specific output columns.

    Args:
        args (argparse.Namespace): Parsed command line arguments containing the
                                        profile, sample names, output format, and other
                                        optional flags.

    Raises:
        FileNotFoundError: If any required files are not found.
        SystemExit: If any unknown output columns are selected.
    """
    # samples
    samples = combine_sample_argument(samples=args.sample)

    # properties
    properties = {}
    _, values_listofdict = sonarUtils.get_all_properties()
    allowedprop = [x["name"] for x in values_listofdict]
    for property_name in allowedprop:
        if hasattr(args, property_name):
            properties[property_name] = getattr(args, property_name)

    # Set output format
    output_format = "count" if args.count else args.format
    # Perform matching
    sonarUtils.match(
        db=args.db,
        profiles=args.profile,
        reference=args.reference,
        samples=samples,
        properties=properties,
        outfile=args.out,
        output_column=args.out_cols,
        format=output_format,
        showNX=args.showNX,
        annotation_type=args.anno_type,
        annotation_impact=args.anno_impact,
        # frameshifts_only=args.frameshifts_only,
        exclude_annotation=args.ex_anno,
        with_sublineage=args.with_sublineage,
        defined_props=values_listofdict,
    )


def handle_list_ref(args: argparse.Namespace):
    print(
        tabulate(sonarUtils.get_all_references(), headers="keys", tablefmt="fancy_grid")
    )
    return


def handle_add_ref(args: argparse.Namespace):
    sonarUtils.add_ref_by_genebank_file(reference_gbs=args.genbank)


def handle_delete_ref(args: argparse.Namespace):
    # del ref
    if args.reference is None:
        LOGGER.error("No reference is given, please add '--reference' ")
        exit(1)

    LOGGER.warning(
        "When the reference is removed, all samples with this reference will also be removed."
    )
    LOGGER.warning(
        "If you need to import data again, you might have to rebuild a new cache directory."
    )
    force_enabled = getattr(args, "force", False)
    decision = ""
    if not force_enabled:
        while decision not in ("YES", "NO"):
            decision = input("Do you really want to delete this reference? [YES/NO]: ")
            decision = decision.upper()

    if decision == "YES" or force_enabled:
        sonarUtils.delete_reference(args.reference)
        LOGGER.info("Reference deleted.")
    else:
        LOGGER.info("Reference not deleted.")


def handle_list_prop(args: argparse.Namespace):
    """
    Handle listing properties from the database.
    This function retrieves all properties stored in the database, sorts them by
    name, and formats the output as a table. The table includes columns such as
    name, argument, subject, description, data type, query type, and standard value.
    The formatted table is then printed to the console.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
    """

    keys, values_listofdict = sonarUtils.get_all_properties()
    rows = [x.values() for x in values_listofdict]
    print(tabulate(rows, headers=keys, tablefmt="fancy_grid"))


def handle_add_prop(args: argparse.Namespace):
    """
    Handle adding a new property to the database.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
    """
    #
    # value_varchar is best suited for storing short to medium-length strings,
    # while value_text is better suited for storing large amounts of textual data.

    # Define a mapping for dtype to qtype and their respective conversion functions
    dtype_mapping = {
        "value_integer": (
            "numeric",
            lambda v: convert_default(
                v, int, f"Cannot convert default value '{v}' to integer."
            ),
        ),
        "value_float": (
            "float",
            lambda v: convert_default(
                v, float, f"Cannot convert default value '{v}' to float."
            ),
        ),
        "value_varchar": ("varchar", str),
        "value_text": ("text", str),
        "value_date": (
            "date",
            lambda v: convert_default(
                v,
                lambda x: datetime.strptime(x, "%Y-%m-%d").date(),
                f"Cannot convert default value '{v}' to date. Expected format: YYYY-MM-DD.",
            ),
        ),
        "value_zip": ("zip", str),
    }

    # Get qtype and conversion function
    if args.dtype in dtype_mapping:
        args.qtype, converter = dtype_mapping[args.dtype]
        args.default = converter(args.default) if converter else None
    elif args.dtype == "value_blob":
        LOGGER.info("This type is not supported yet.")
        args.qtype, args.default = None, None
    else:
        LOGGER.info("This type is not supported.")
        args.qtype, args.default = None, None

    # Call the utility function
    sonarUtils.add_property(
        args.name,
        args.dtype,
        args.qtype,
        args.descr,
        args.subject,
        args.default,
    )


def handle_tasks(args: argparse.Namespace):
    if args.verb == "list":
        print(
            tabulate(
                sonarUtils1.get_all_jobs(db=args.db),
                headers="keys",
                tablefmt="fancy_grid",
            )
        )
    elif args.verb in {"show", "watch"}:
        result, status = sonarUtils1.get_job_byID(
            db=args.db,
            job_id=args.jobid,
            background=args.verb == "watch",
            interval=getattr(args, "interval", 60),
        )
        print("Status:", status)
        print(
            tabulate(
                result,
                headers="keys",
                tablefmt="grid",
            )
        )


def handle_delete_prop(args: argparse.Namespace):
    """
    Handle deleting an existing property from the database.

    This function removes a specified property from the database. If the 'force'
    option is not set, the user is prompted to confirm the deletion, especially
    when there are samples with non-default values for the property.

    Args:
    args (argparse.Namespace): Parsed command line arguments containing the
    property name to be deleted and the 'force' flag.

    Raises:
    SystemExit: If the specified property name is not found in the database.
    """
    force_enabled = getattr(args, "force", False)
    decision = ""
    if not force_enabled:
        while decision not in ("yes", "no"):
            decision = input(
                "Do you really want to delete this property? [YES/no]: "
            ).lower()

    if decision.lower() == "yes" or force_enabled:
        sonarUtils.delete_property(name=args.name)
    else:
        LOGGER.info("Property is not deleted.")


def handle_delete_sample(args: argparse.Namespace):
    """
    Handle deleting a sample from the database.

    This function removes specified samples from the database. The samples can be
    provided as command line arguments or within a file. If the 'force' option is
    not set, the user is prompted to confirm the deletion, especially when there
    are samples with non-default values for any property.

    Args:
        args (argparse.Namespace): Parsed command line arguments containing the
                                        sample names to be deleted and the 'force' flag.

    Raises:
        FileNotFoundError: If the specified sample file is not found.
        SystemExit: If none of the specified samples are found in the database.
    """
    force_enabled = getattr(args, "force", False)
    decision = ""

    if not force_enabled:
        while decision not in ("YES", "NO"):
            decision = input("Are you sure you want to perform this action? [YES/NO]: ")
            decision = decision.upper()

    if decision == "YES" or force_enabled:
        samples = combine_sample_argument(
            samples=args.sample, sample_files=args.sample_file
        )
        sonarUtils.delete_sample(samples=samples)  # reference=args.reference,


def handle_delete_sequence(args: argparse.Namespace):
    """
    Handle deleting a sequence from the database.

    This function removes specified sequences from the database. The sequences can be
    provided as command line arguments or within a file. If the 'force' option is
    not set, the user is prompted to confirm the deletion.

    Args:
        args (argparse.Namespace): Parsed command line arguments containing the
                                        sequence names to be deleted and the 'force' flag.

    Raises:
        FileNotFoundError: If the specified sample file is not found.
        SystemExit: If none of the specified samples are found in the database.
    """
    force_enabled = getattr(args, "force", False)
    decision = ""

    if not force_enabled:
        while decision not in ("YES", "NO"):
            decision = input("Are you sure you want to perform this action? [YES/NO]: ")
            decision = decision.upper()

    if decision == "YES" or force_enabled:
        sequences = combine_sample_argument(
            samples=args.sequence, sample_files=args.sequence_file
        )
        sonarUtils.delete_sequence(sequences=sequences)  # reference=args.reference,


def handle_lineage(args: argparse.Namespace):
    sonarUtils1.upload_lineage(
        pathogen=args.pathogen, lineage_file=args.lineage, output_file=args.out
    )


def handle_info(args: argparse.Namespace):
    sonarUtils1.get_info(db=args.db)


def execute_commands(args):  # noqa: C901
    """
    Execute the appropriate function based on the provided command.
    This function determines which command was provided as an argument and
    calls the corresponding function to handle the command. It also ensures
    the database compatibility before executing the command.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
    """
    LOGGER.info(f"Current version {NAME}:{get_version()}")
    if args.resource == "sample" and args.verb == "import":
        handle_import(args)
    elif args.resource == "reference" and args.verb == "add":
        handle_add_ref(args)
    elif args.resource == "reference" and args.verb == "list":
        handle_list_ref(args)
    elif args.resource == "reference" and args.verb == "delete":
        handle_delete_ref(args)
    elif args.resource == "property" and args.verb == "list":
        handle_list_prop(args)
    elif args.resource == "property" and args.verb == "add":
        handle_add_prop(args)
    elif args.resource == "property" and args.verb == "delete":
        handle_delete_prop(args)
    elif args.resource == "sample" and args.verb == "match":
        handle_match(args)
    elif args.resource == "sample" and args.verb == "delete":
        handle_delete_sample(args)
    elif args.resource == "sequence" and args.verb == "delete":
        handle_delete_sequence(args)
    elif args.resource == "task":
        handle_tasks(args)
    elif args.resource == "lineage" and args.verb == "import":
        handle_lineage(args)
    elif args.resource == "dataset" and args.verb == "import":
        handle_import_dataset(args)
    elif args.resource == "info" and args.verb == "show":
        handle_info(args)


def main(args: Optional[argparse.Namespace] = None) -> int:
    """
    The main function that handles the execution of different commands.

    Args:
        args (Optional[argparse.Namespace]): Namespace containing parsed command-line arguments.
            If None, the function will parse the arguments itself.

    Returns:
        int: Returns 0 if finished successfully.
    """

    if not args:
        args = parse_args(sys.argv[1:])

    # Set debugging mode
    if hasattr(args, "verbose") and args.verbose:
        config.DEBUG = True
    else:
        config.DEBUG = False

    LoggingConfigurator(debug=config.DEBUG)
    config.set_runtime_override("API_URL", getattr(args, "db", None))

    execute_commands(args)

    return 0


def run():
    parsed_args = parse_args(sys.argv[1:])
    main(parsed_args)


if __name__ == "__main__":
    run()
