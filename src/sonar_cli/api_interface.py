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
    get_alignment_endpoint = "alignments/get_alignment_data"
    get_gene_endpoint = "genes/get_gene_data"
    get_replicon_endpoint = "replicons/get_molecule_data"
    get_match_endpoint = "samples/genomes"

    get_translation_table_endpoint = "resources/get_translation_table"
    get_properties_endpont = "property/get_all_properties"

    post_add_reference_endpoint = "references/import_gbk/"
    post_delete_reference_endpoint = "references/delete_reference/"
    post_delete_sample_endpoint = "samples/delete_sample_data/"
    post_import_property_upload_endpoint = "samples/import_properties_tsv/"
    post_import_upload_endpoint = "file_uploads/import_upload/"

    def __init__(self, base_url, token=""):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = {},
        data: dict | None = {},
        files: dict | None = {},
        headers: dict | None = {},
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
                params=params,
                files=files,
                verify=True,
            )
            return_json = response.json()
            #   response.raise_for_status() for HTTP errors (4xx, 5xx)
            if 400 <= response.status_code < 500:
                # Handle client-side errors (e.g., bad request)
                LOGGER.error(
                    f"{response.status_code} Client Error: {response.reason}: {return_json['message']} "
                )
            elif 500 <= response.status_code < 600:
                LOGGER.error(
                    f"{response.status_code} Server Error: {response.reason} for url: {url}"
                )
                sys.exit(1)

        except requests.exceptions.HTTPError as errh:
            LOGGER.error(f"HTTP Error: {errh}")
            response.raise_for_status()
            sys.exit(1)
        except requests.exceptions.RequestException as err:
            LOGGER.error(f"Request Exception: {err}")
            response.raise_for_status()
            sys.exit(1)

        return return_json

    def get_all_references(self):
        """
        Returns:
            List[str]: A list of references
        """
        json_response = self._make_request(
            "GET", endpoint=self.get_all_references_endpoint
        )
        try:
            data = json_response["data"]
            # if not data:
            #    raise ValueError("No data found in the response.")
            return data

        # TODO: can we move this except to the def _make_request, so we dont repeat the code
        except KeyError:
            raise ValueError("Invalid JSON response. 'data' key not found.")
        except Exception as e:
            raise ValueError(f"Error processing JSON response: {str(e)}")

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
        try:
            data = json_response["data"]
            # if not data:
            #    raise ValueError("No data found in the response.")
            return data
        except KeyError:
            raise ValueError("Invalid JSON response. 'data' key not found.")
        except Exception as e:
            raise ValueError(f"Error processing JSON response: {str(e)}")

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
        if json_response["data"]:
            data = json_response["data"]
            return (data["sample_id"], data["sequence__seqhash"])
        else:
            return (None, None)

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
        if json_response["data"]:
            data = json_response["data"]
            return data["id"]
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
            {'NC_063383.1': {'molecule.accession': 'NC_063383.1',
            'molecule.id': 1, 'molecule.standard': 1,
            'translation.id': 1}}
        """
        params = {}
        params["reference_accession"] = reference_accession
        json_response = self._make_request(
            "GET", endpoint=self.get_replicon_endpoint, params=params
        )
        if json_response["data"]:
            row = json_response["data"]

            return {x["accession"]: x for x in row}
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
        if json_response["data"]:
            data = json_response["data"][0]
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
        if json_response["data"]:
            data = json_response["data"]
            return data
        else:
            return None

    def get_translation_dict(self, translation_id):
        """
        Returns all elements based on given molecule id

        Returns:
            Optional[list]: The list of element if it exists, None otherwise.
        """
        params = {}
        params["translation_id"] = translation_id
        json_response = self._make_request(
            "GET", endpoint=self.get_translation_table_endpoint, params=params
        )
        if json_response["data"]:
            data = json_response["data"]
            return data
        else:
            return None

    def post_import_upload(self, files):
        """
        send compressed sample, var, vcf file.
        """
        json_response = self._make_request(
            "POST", endpoint=self.post_import_upload_endpoint, files=files
        )
        if json_response["status"] == "success":

            return True
        else:
            return False

    def post_add_reference(self, reference_gb_obj):
        """
        send gbk file.
        """

        data = {"translation_id": 1}

        file = {"gbk_file": reference_gb_obj}

        json_response = self._make_request(
            "POST", endpoint=self.post_add_reference_endpoint, data=data, files=file
        )
        if json_response["status"] == "success":
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
        if json_response["status"] == "success":
            return True, ""
        else:
            return False, json_response["message"]

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
