import sys
import time

from sonar_cli.api_interface import APIClient
from sonar_cli.common_utils import _files_exist
from sonar_cli.config import BASE_URL
from sonar_cli.lineages.sc2_lineages import main as sc2_main
from sonar_cli.logging import LoggingConfigurator

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()
bar_format = "{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]"


class sonarUtils1:
    """
    A class used to perform operations on a Tool's.
    """

    overall_status_dict = {
        "Q": "Queued",
        "IP": "In Progress",
        "C": "Completed",
        "F": "Failed",
    }

    def __init__(self):
        pass

    @staticmethod
    def get_info(db: str = None):
        API_URL = BASE_URL if db is None else db

        json_response = APIClient(base_url=API_URL).get_database_info()
        log_message = "No information available"
        if len(json_response["detail"]) != 0:
            data = json_response["detail"]
            log_message = "\n".join(
                [
                    "Meta Data Coverage:",
                    *[
                        f"   {key}: {value}"
                        for key, value in data["metadata_coverage"].items()
                    ],
                    f"Samples Total: {data['samples_total']}",
                    f"Earliest Sampling Date: {data['earliest_sampling_date']}",
                    f"Latest Sampling Date: {data['latest_sampling_date']}",
                    f"Database Size: {data['database_size']}",
                    f"Database Version: {data['database_version']}",
                    f"Earliest Genome Import: {data['earliest_genome_import']}",
                    f"Latest Genome Import: {data['latest_genome_import']}",
                ]
            )

        LOGGER.info(log_message)

        # Display reference genomes information for all organisms
        if "reference_genomes" in data and data["reference_genomes"]:
            for organism, ref_info in data["reference_genomes"].items():
                LOGGER.info(f"\nReference Genome: {organism}")
                LOGGER.info(f"  Replicons: {', '.join(ref_info['replicons'])}")
                LOGGER.info(
                    f"  Reference Length: {', '.join(map(str, ref_info['reference_length']))} bp"
                )
                LOGGER.info(f"  Annotated Proteins: {ref_info['annotated_proteins']}")
                LOGGER.info(f"  Unique Sequences: {ref_info['unique_sequences']}")
                LOGGER.info(f"  Genomes: {ref_info['genomes']}")

    @staticmethod
    def get_all_jobs(db: str = None):
        API_URL = BASE_URL if db is None else db

        json_response = APIClient(base_url=API_URL).get_all_jobs()
        if not json_response or len(json_response["detail"]) == 0:
            return {"job_name": "", "status": "", "entry_time": ""}

        # only necessary column
        modified_data = [
            {
                "job_name": entry["job_name"],
                "status": entry["status"],
                "entry_time": entry["entry_time"],
            }
            for entry in json_response["detail"]
        ]

        return modified_data

    @staticmethod
    def fetch_job_status(API_URL, job_id):
        json_response = APIClient(base_url=API_URL).get_job_byID(job_id)
        overall_status = sonarUtils1.overall_status_dict[json_response["status"]]
        if not json_response or len(json_response["detail"]) == 0:
            return {
                "file_name": "",
                "status": "",
            }, overall_status

        # only necessary column
        modified_data = [
            {
                "file_name": entry["file_name"],
                "status": (
                    "\n".join(
                        "{!r}: {!r},".format(k, v)
                        for k, v in entry["status_list"][0].items()
                    )
                    if len(entry["status_list"]) > 0
                    else "Processing..."
                ),
            }
            for entry in json_response["detail"]
        ]

        return modified_data, overall_status

    @staticmethod
    def get_job_byID(db: str = None, job_id=None, background=False, interval=180):
        API_URL = BASE_URL if db is None else db

        if background:
            LOGGER.info(
                "Print status only every fifth time to prevent too much output."
            )
            LOGGER.info(f"Background command entered with interval {interval} seconds.")
            counter = 0
            try:
                while True:
                    modified_data, overall_status = sonarUtils1.fetch_job_status(
                        API_URL, job_id
                    )
                    if overall_status in ["Completed", "Failed"]:
                        return modified_data, overall_status
                    elif overall_status in ["Queued", "In Progress"]:
                        if counter % 5 == 0:
                            LOGGER.info("Job is {}...".format(overall_status.lower()))
                            counter = 0
                        counter += 1
                    time.sleep(interval)
            except KeyboardInterrupt:
                LOGGER.warning("Process interrupted by user. Exiting...")
                sys.exit(1)
        else:
            return sonarUtils1.fetch_job_status(API_URL, job_id)

    @staticmethod
    def upload_lineage(pathogen: str, lineage_file: str, output_file: str):
        LOGGER.info("Using Pathogen: %s", pathogen)

        if not lineage_file:
            LOGGER.info("No lineage file provided. Generating lineage file...")
            if output_file is None:
                output_file = "lineages.tsv"
                LOGGER.info(
                    "Output file not provided. Using default file name: %s", output_file
                )
            if pathogen == "SARS-CoV-2":
                lineage_file = sc2_main(output_file=output_file)
            else:
                pass
        else:
            _files_exist(lineage_file)
            LOGGER.info("Lineage file provided: %s", lineage_file)
            LOGGER.info("No download is required, lineage file generation is skipped.")

        if lineage_file:
            LOGGER.info("Uploading lineage file to the server...")

            lineage_obj = open(lineage_file, "rb")
            try:
                json_response = APIClient(base_url=BASE_URL).put_lineage_import(
                    lineage_obj
                )
                if json_response["detail"] == "Lineages updated successfully":
                    LOGGER.info("The lineage has been updated successfully.")
                else:
                    LOGGER.error("The lineage failed to be updated.")
            except Exception as e:
                LOGGER.exception(e)
                LOGGER.error("Fail to process lineage file")
                raise
