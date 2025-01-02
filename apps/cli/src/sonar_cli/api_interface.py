import json
import sys
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import requests
from sonar_cli.logging import LoggingConfigurator

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()


class APIClient:
    get_all_references_endpoint = "references/get_all_references"
    get_distinct_accession_endpoint = "references/distinct_accessions"
    get_sample_data_endpoint = "samples/get_sample_data"
    get_bulk_sample_data_endpoint = "samples/get_bulk_sample_data/"
    get_alignment_endpoint = "alignments/get_alignment_data"
    get_bulk_alignment_endpoint = "alignments/get_bulk_alignment_data/"
    get_gene_endpoint = "genes/get_gene_data"
    get_replicon_endpoint = "replicons/get_molecule_data"
    get_match_endpoint = "samples/genomes"
    get_reference_genbank_endpoint = "references/get_reference_file"
    get_translation_table_endpoint = "resources/get_translation_table"
    get_properties_endpont = "properties/get_all_properties"

    get_all_jobs_endpont = "tasks/get_all_jobs"
    get_jobID_endpont = "tasks/generate_job_id"
    get_job_byID_endpont = "tasks/get_files_by_job_id"

    get_database_info_endpont = "database/get_database_info"

    post_add_reference_endpoint = "references/import_gbk/"
    post_delete_reference_endpoint = "references/delete_reference/"
    post_delete_sample_endpoint = "samples/delete_sample_data/"
    post_import_property_upload_endpoint = "samples/import_properties_tsv/"
    post_import_upload_endpoint = "file_uploads/import_upload/"
    post_add_property_endpoint = "properties/add_property/"
    post_delete_property_endpoint = "properties/delete_property/"

    put_lineage_import_endpoint = "lineages/update_lineages/"

    def __init__(self, base_url, token=""):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = {},
        data: dict | None = {},
        json: dict | None = {},
        files: dict | None = {},
        headers: dict | None = {},
        stream: bool = False,  # stream flag for file downloads
    ):
        if headers:
            self.headers.update(headers)
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.request(
                method,
                url,
                headers=self.headers,
                data=data,
                json=json,
                params=params,
                files=files,
                verify=True,
                stream=stream,
                # timeout=300,
            )
            if not stream:
                return_json = response.json()
                #   response.raise_for_status() for HTTP errors (4xx, 5xx)
                if 400 <= response.status_code < 500:
                    # Handle client-side errors (e.g., bad request)
                    # message = return_json["message"] if "message" in return_json else ""
                    LOGGER.error(
                        f"{response.status_code} Client Error: {response.reason}: {return_json} "
                    )
                    LOGGER.error("Immediately stop running and exit")
                    sys.exit(1)
                elif 500 <= response.status_code < 600:
                    LOGGER.error(
                        f"{response.status_code} Server Error: {response.reason} for url: {url}"
                    )
                    LOGGER.error("Immediately stop running and exit")
                    sys.exit(1)

                return return_json
            else:
                return response
        except requests.exceptions.ConnectionError as errc:
            LOGGER.error(f"Error Connecting: {errc}")
            sys.exit(1)
        except requests.exceptions.Timeout as errt:
            LOGGER.error(f"Timeout Error: {errt}")
            # LOGGER.warn("We set timeout 300 secs")
            sys.exit(1)
        except requests.exceptions.HTTPError as errh:
            LOGGER.error(f"HTTP Error: {errh}")
            sys.exit(1)
        except requests.exceptions.RequestException as err:
            LOGGER.error(f"Request Exception: {err}")
            LOGGER.error(f"at request: {url}")
            LOGGER.error(response)
            response.raise_for_status()
            sys.exit(1)

    def get_all_references(self):
        """
        Returns:
            List[str]: A list of references
        """
        json_response = self._make_request(
            "GET", endpoint=self.get_all_references_endpoint
        )
        return json_response

    def get_all_properties(self):
        """
        Returns:
            List[str]: A list of properties
        """
        json_response = self._make_request("GET", endpoint=self.get_properties_endpont)

        return json_response

    def get_distinct_reference(self):
        """
        Json response example:
            {
                "data": [
                    "MN908947.3"
                ]
            }

        Returns:
            List[str]: A list of accession
        """
        json_response = self._make_request(
            "GET", endpoint=self.get_distinct_accession_endpoint
        )
        return json_response

    def get_bulk_sample_data(self, sample_name_list: List[str]):
        data = {"sample_data": sample_name_list}
        json_response = self._make_request(
            "POST", endpoint=self.get_bulk_sample_data_endpoint, json=data
        )
        return json_response

    def get_sample_data(self, sample_name: str):
        """
        Returns a tuple of rowid and seqhash of a sample based on its name if it exists,
        else a tuple of Nones is returned.

        Args:
            sample_name (str): Name of the sample.

        Json response example:
            "data": {
                "sample_id": 316,
                "name": "IMS-10186-CVDP-95BECAEB-031A-46D1-ACF1-1730927B1F6F",
                "sequence__seqhash": "69621864a082dcddfca3fbe04cf3cd9c9c14e7fc8adc28b302259acfc9d43b63"
            }

        Returns:
            Optional[Tuple[int,str]]: Tuple of id and seqhash of the sample,
            if exists, else a Tuple of None, None.
        """
        params = {}
        params["sample_data"] = sample_name
        json_response = self._make_request(
            "GET", endpoint=self.get_sample_data_endpoint, params=params
        )
        if len(json_response) > 0:
            return (json_response["sample_id"], json_response["sequence__seqhash"])
        else:
            return (None, None)

    def get_bulk_alignment_data(self, rep_seq_list: List[dict]):
        data = {"sample_data": rep_seq_list}
        json_response = self._make_request(
            "POST", endpoint=self.get_bulk_alignment_endpoint, json=data
        )
        return json_response

    def get_alignment_id(self, seqhash: str, element_id: int):
        """
        Returns the rowid of a sample based on the respective seqhash and element. If no
        alignment of the given sequence to the given element has been stored, None is returned.

        Args:
            seqhash (str): The seqhash of the sample.
            element_id (int): The element id. (replicon id)

        Returns:
            Optional[int]: The id of the alignment if exists, else None.

        """
        params = {}
        url = f"{self.get_alignment_endpoint}/{seqhash}/{element_id}/"
        json_response = self._make_request("GET", endpoint=url, params=params)

        if len(json_response) > 0:
            return json_response["id"]
        else:
            return None

    def get_molecule_data(
        self, *fields, reference_accession: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Returns a dictionary with molecule accessions as keys and sub-dicts as values for all molecules
        of a given (or the default) reference. The sub-dicts store all table field names
        (or, alternatively, the given table field names only) as keys and the stored data as values.

        Args:
            *fields: Fields to be included in the sub-dicts.
            reference_accession (str, optional): The reference accession. Defaults to None, which means the default reference.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary with molecule accessions as keys and their data as values.

            Examples:
            {"id": 1,
                        "length": 29903,
                        "sequence": "ATCG"
                        "accession": "MN908947.3",
                        "description": "Severe acute respiratory syndrome coronavirus 2 isolate Wuhan-Hu-1, complete genome",
                        "type": null,
                        "segment_number": null,
                        "reference_id": 1,
                        "translation_id": 1
            }
        """
        params = {}
        params["reference_accession"] = reference_accession
        json_response = self._make_request(
            "GET", endpoint=self.get_replicon_endpoint, params=params
        )
        if len(json_response) > 0:
            list_of_dict = json_response
            return {x["accession"]: x for x in list_of_dict}
        else:
            return {}

    def get_source(self, molecule_id: int) -> Optional[str]:
        """
        Returns the source data given a molecule id (replicon ID).

        Args:
            molecule_id (replicon ID) (int): The id of the molecule.

        Returns:
            Optional[str]: The source if it exists, None otherwise.

        Example usage:
        >>> dbm = getfixture('init_readonly_dbm')
        >>> dbm.get_source(molecule_id=5)
        >>> dbm.get_source(molecule_id=1)['accession']
        'MN908947.3'
        """
        # sql = "SELECT * FROM replicon WHERE replicon_id = ?"
        params = {}
        params["replicon_id"] = molecule_id
        json_response = self._make_request(
            "GET", endpoint=self.get_replicon_endpoint, params=params
        )
        if len(json_response) > 0:
            data = json_response[0]
            return data
        else:
            return None

    def get_elements(self, molecule_id=None, ref_acc=None, molecule_acc=None):
        """
        Returns all elements (Gene) based on given molecule id

        Args:
            ref_acc (str): reference accesion

        Returns:
            Optional[list]: The list of element if it exists, None otherwise.
        """
        params = {}
        if molecule_id:
            params["replicon_id"] = molecule_id

        if ref_acc:
            params["ref_acc"] = ref_acc

        if molecule_acc:
            params["molecule_acc"] = molecule_acc

        json_response = self._make_request(
            "GET", endpoint=self.get_gene_endpoint, params=params
        )
        if len(json_response) > 0:
            return json_response
        else:
            return None

    # def get_translation_dict(self, translation_id):
    #     NOTE: no longer use, will be removed
    #     """
    #     Returns all elements based on given molecule id

    #     Returns:
    #         Optional[list]: The list of element if it exists, None otherwise.
    #     """
    #     params = {}
    #     params["translation_id"] = translation_id
    #     json_response = self._make_request(
    #         "GET", endpoint=self.get_translation_table_endpoint, params=params
    #     )
    #     if json_response["data"]:
    #         data = json_response["data"]
    #         return data
    #     else:
    #         return None

    def post_import_upload(self, files, job_id=None, data={}):
        """
        send compressed sample, var, vcf file.
        """
        if job_id and not data:
            data = {"job_id": job_id}

        json_response = self._make_request(
            "POST", endpoint=self.post_import_upload_endpoint, data=data, files=files
        )
        return json_response

    def post_add_reference(self, reference_gb_obj):
        """
        send gbk file.
        """

        data = {"translation_id": 1}

        file = {"gbk_file": reference_gb_obj}

        json_response = self._make_request(
            "POST", endpoint=self.post_add_reference_endpoint, data=data, files=file
        )
        if json_response["detail"] == "File uploaded successfully":
            return True
        else:
            return False

    def post_delete_reference(self, reference_accession):
        """ """
        data = {"accession": reference_accession}

        json_response = self._make_request(
            "POST", endpoint=self.post_delete_reference_endpoint, data=data
        )
        return json_response

    def post_import_property_upload(self, data, file):
        json_response = self._make_request(
            "POST",
            endpoint=self.post_import_property_upload_endpoint,
            data=data,
            files=file,
        )
        return json_response

    def get_variant_profile_bymatch_command(self, params: dict):

        json_response = self._make_request(
            "GET", endpoint=self.get_match_endpoint, params=params
        )
        return json_response

    def post_delete_sample(self, reference_accession, samples: List[str] = []):
        data = {
            "reference_accession": reference_accession,
            "sample_list": json.dumps(samples),
        }

        json_response = self._make_request(
            "POST",
            endpoint=self.post_delete_sample_endpoint,
            data=data,
        )
        return json_response

    def post_add_property(self, data: dict):
        json_response = self._make_request(
            "POST",
            endpoint=self.post_add_property_endpoint,
            data=data,
        )
        return json_response

    def post_delete_property(self, name: str):
        """ """
        data = {"name": name}

        json_response = self._make_request(
            "POST", endpoint=self.post_delete_property_endpoint, data=data
        )
        return json_response

    def get_all_jobs(self):
        """
        Returns:
            List[str]: A list of references
        """
        json_response = self._make_request("GET", endpoint=self.get_all_jobs_endpont)
        return json_response

    def get_job_byID(self, job_id: str):
        """ """
        params = {}
        params["job_id"] = job_id
        json_response = self._make_request(
            "GET", endpoint=self.get_job_byID_endpont, params=params
        )
        return json_response

    def put_lineage_import(self, lineage_obj):
        """
        send lineage file.
        """

        file = {"lineages_file": lineage_obj}

        json_response = self._make_request(
            "PUT", endpoint=self.put_lineage_import_endpoint, files=file
        )
        return json_response

    def get_jobID(self, is_prop_job: bool = False):
        """
        Returns:
            List[str]: A list of references
        """
        params = {}
        params["is_prop"] = is_prop_job
        json_response = self._make_request(
            "GET", endpoint=self.get_jobID_endpont, params=params
        )
        return json_response

    def get_database_info(
        self,
    ):
        params = {}

        json_response = self._make_request(
            "GET", endpoint=self.get_database_info_endpont, params=params
        )
        return json_response

    def get_reference_genbank(self, params: dict):
        response = self._make_request(
            "GET",
            endpoint=self.get_reference_genbank_endpoint,
            params=params,
            stream=True,
        )
        return response
