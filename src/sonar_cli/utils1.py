import sys
import time

from sonar_cli.api_interface import APIClient
from sonar_cli.config import BASE_URL
from sonar_cli.logging import LoggingConfigurator

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()
bar_format = "{desc} {percentage:3.0f}% [{n_fmt}/{total_fmt}, {elapsed}<{remaining}, {rate_fmt}{postfix}]"


class sonarUtils1:
    """
    A class used to perform operations on a Tool's.
    """

    def __init__(self):
        pass

    # DATA IMPORT
    @staticmethod
    def get_all_jobs(db: str = None):
        if db is None:
            API_URL = BASE_URL
        else:
            API_URL = db

        json_response = APIClient(base_url=API_URL).get_all_jobs()
        if not json_response or len(json_response["detail"]) == 0:
            return {"job_name": "", "status": "", "entry_time": ""}
        # only neccessary column
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
    def get_job_byID(  # noqa: C901
        db: str = None, job_id=None, background=False, interval=180
    ):
        API_URL = BASE_URL if db is None else db
        overall_status_dict = {
            "Q": "Queued",
            "IP": "In Progress",
            "C": "Completed",
            "F": "Failed",
        }

        def fetch_job_status():
            json_response = APIClient(base_url=API_URL).get_job_byID(job_id)
            overall_status = overall_status_dict[json_response["status"]]
            if not json_response or len(json_response["detail"]) == 0:
                return {
                    "file_name": "",
                    "status": "",
                }, overall_status
            # only neccessary column

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

        if background:
            LOGGER.info(
                "Print status only every fifth time to prevent too much output."
            )
            LOGGER.info(f"Background command entered with interval {interval} seconds.")
            counter = 0
            try:
                while True:
                    modified_data, overall_status = fetch_job_status()
                    if overall_status in ["Completed", "Failed"]:
                        return modified_data, overall_status
                    elif overall_status == "Queued" or overall_status == "In Progress":
                        if counter % 5 == 0:
                            LOGGER.info("Job is {}...".format(overall_status.lower()))
                            counter = 0
                        counter += 1
                    time.sleep(interval)
            except KeyboardInterrupt:
                LOGGER.warning("Process interrupted by user. Exiting...")
                sys.exit(1)
        else:
            return fetch_job_status()
