import argparse
import sys
from typing import Optional

from sonar_cli.logging import LoggingConfigurator
from sonar_cli.utils import sonarUtils

from . import DESCRIPTION
from . import NAME
from . import VERSION

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
    parser = argparse.ArgumentParser(
        prog="sonar-cli",
        description=f"{NAME} {VERSION}: {DESCRIPTION}",
    )
    general_parser = create_parser_general()
    database_parser = create_parser_database()
    output_parser = create_parser_output()
    sample_parser = create_parser_sample()
    # property_parser = create_parser_property()
    reference_parser = create_parser_reference()
    thread_parser = create_parser_thread()

    # Create all subparsers for the command-line interface
    subparsers = parser.add_subparsers(dest="command", required=True)
    # import parser
    subparsers, _ = create_subparser_list_reference(subparsers, database_parser)
    subparsers, _ = create_subparser_import(
        subparsers, database_parser, thread_parser, reference_parser
    )
    subparsers, _ = create_subparser_list_prop(subparsers, database_parser)

    subparsers, subparser_match = create_subparser_match(
        subparsers,
        database_parser,
        reference_parser,
        sample_parser,
        output_parser,
        general_parser,
    )

    # version parser
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{NAME}:{VERSION}",
        help="Show program's version number and exit.",
    )

    # register known arguments
    # add database-specific properties to match subparser
    user_namespace = args_namespace()
    known_args, _ = parser.parse_known_args(args=args, namespace=user_namespace)

    return parser.parse_args(args=args, namespace=user_namespace)


def create_parser_general() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--debug",
        help="activate debugging mode showing all queries and debug info on screen",
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
        default=None,
    )
    return parser


def create_parser_database() -> argparse.ArgumentParser:
    """Creates a 'database' parent parser with common arguments and options for the command-line interface.

    Returns:
        argparse.ArgumentParser: The created 'database' parent parser.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--db", metavar="URL", help="URL to sonar database", type=str)
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

    parser.add_argument(
        "--out-column",
        help="select output columns to the output file (support csv and tsv)",
        type=str,
        default="all",
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
        help="number of threads to use (default: 1)",
        type=int,
        default=1,
    )
    return parser


def create_subparser_list_prop(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    """
    Creates a 'list-prop' subparser with command-specific arguments and options for the command-line interface.

    Args:
        subparsers (argparse._SubParsersAction): ArgumentParser object to attach the 'list-prop' subparser to.
        parent_parsers (argparse.ArgumentParser): ArgumentParser objects providing common arguments and options.

    Returns:
        argparse.ArgumentParser: The created 'list-prop' subparser.
    """
    parser = subparsers.add_parser(
        "list-prop",
        help="List all sample properties added to the database",
        parents=parent_parsers,
    )
    return subparsers, parser


def create_subparser_list_reference(
    subparsers: argparse._SubParsersAction, *parent_parsers: argparse.ArgumentParser
) -> argparse.ArgumentParser:

    # View Reference.
    parser = subparsers.add_parser(
        "list-ref",
        parents=parent_parsers,
        help="List all available references in the database",
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
        help="import genome sequences and sample properties into the database",
        parents=parent_parsers,
    )

    parser.add_argument(
        "--method",
        help="Select alignment tools: 1. MAFFT 2. Parasail (default 1)",
        type=int,
        default=1,
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
        help="assign column names used in the provided TSV/CSV file to the matching property names provided by the database in the form PROP=COL (e.g. SAMPLE=GenomeID)",
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
        "--no-update",
        help="skip samples already existing in the database (default: False (no skip)",
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
        "-p",
        help="don't show progress bars while importing",
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
        help="match samples based on mutation profiles and/or properties",
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
    parser.add_argument(
        "--frameshifts-only",
        help="match only mutation profiles with frameshift mutations",
        action="store_true",
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
        help="output format (default: tsv)",
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

    if args.method == 1:
        LOGGER.info("Alignment Tool: MAFFT")
    elif args.method == 2:
        LOGGER.info("Alignment Tool: Parasail")
    else:
        print("Invalid method. Please choose 1 for MAFFT or 2 for Parasail.")
        exit(1)

    sonarUtils.import_data(
        # db=args.db,
        fasta=args.fasta,
        csv_files=args.csv,
        tsv_files=args.tsv,
        prop_links=args.cols,
        cachedir=args.cache,
        autolink=args.auto_link,
        auto_anno=args.auto_anno,
        progress=not args.no_progress,
        update=not args.no_update,
        threads=args.threads,
        quiet=args.debug,
        reference=args.reference,
        method=args.method,
    )


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
    return


def handle_list_ref(args: argparse.Namespace):
    return


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
    return


def execute_commands(args):  # noqa: C901
    """
    Execute the appropriate function based on the provided command.
    This function determines which command was provided as an argument and
    calls the corresponding function to handle the command. It also ensures
    the database compatibility before executing the command.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
    """

    if args.command == "import":
        if len(sys.argv[1:]) == 1:
            parse_args(["import", "-h"])
        else:
            handle_import(args)
    elif args.command == "list-ref":
        handle_list_ref(args)
    elif args.command == "list-prop":
        handle_list_prop(args)
    elif args.command == "match":
        if len(sys.argv[1:]) == 1:
            parse_args(["match", "-h"])
        else:
            handle_match(args)


def main(args: Optional[argparse.Namespace] = None) -> int:
    """
    The main function that handles the execution of different commands.

    Args:
        args (Optional[argparse.Namespace]): Namespace containing parsed command-line arguments.
            If None, the function will parse the arguments itself.

    Returns:
        int: Returns 0 if finished successfully.
    """

    # process arguments
    if not args:
        args = parse_args(sys.argv[1:])
    # Set debugging mode
    if hasattr(args, "debug") and args.debug:
        debug = True
    else:
        debug = False
        args.debug = False

    LoggingConfigurator(debug=debug)

    execute_commands(args)

    return 0


def run():
    parsed_args = parse_args(sys.argv[1:])
    main(parsed_args)


if __name__ == "__main__":
    run()
