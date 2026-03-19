"""
Pathoplexus Dataset Importer.

Downloads and processes pathogen sequence data from Pathoplexus using the LAPIS API.

API Documentation: https://pathoplexus.org/docs/how-to/search-download-seqs-api
LAPIS API Base: https://lapis.pathoplexus.org/

Supported organisms:
- cchf (Crimean-Congo Hemorrhagic Fever) - segmented, not yet supported
- west-nile (West Nile Virus)
- ebola-zaire (Ebola Zaire)
- ebola-sudan (Ebola Sudan)
- mpox (Mpox Virus)
- hmpv (Human Metapneumovirus)
- rsv-a (RSV-A)
- rsv-b (RSV-B)
- measles (Measles Virus)
- marburg (Marburg Virus)
"""

import csv
import datetime
import json
from pathlib import Path
import random
import shutil
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import requests

from .base import DatasetImporter
from .utils import LOGGER

# LAPIS API base URL
LAPIS_BASE_URL = "https://lapis.pathoplexus.org"


def normalize_date_format(date_str: str) -> str:
    """
    Normalize date string to ISO format (YYYY-MM-DD).

    Handles various date formats from Pathoplexus:
    - Empty string -> Empty string
    - YYYY -> YYYY-01-01
    - YYYY-MM -> YYYY-MM-01
    - YYYY-MM-DD -> YYYY-MM-DD (unchanged)

    Args:
        date_str: Date string in various formats

    Returns:
        Normalized date string in YYYY-MM-DD format or empty string
    """
    if not date_str or not date_str.strip():
        return ""

    date_str = date_str.strip()
    parts = date_str.split("-")

    try:
        if len(parts) == 1:
            # Only year (YYYY)
            date_str = f"{parts[0]}-01-01"
        elif len(parts) == 2:
            # Year and month (YYYY-MM)
            date_str = f"{parts[0]}-{parts[1]}-01"
        elif len(parts) == 3:
            # Full date (YYYY-MM-DD) - keep as is
            pass
        else:
            # Invalid format, return empty
            LOGGER.warning(f"Invalid date format (too many parts): {date_str}")
            return ""

        # Validate and format the date using datetime
        default_date = datetime.date.fromisoformat(date_str)
        return default_date.strftime("%Y-%m-%d")

    except (ValueError, TypeError) as e:
        LOGGER.warning(f"Invalid date format '{date_str}': {e}")
        return ""


# Mapping from user-friendly pathogen names to Pathoplexus organism identifiers
PATHOGEN_TO_ORGANISM = {
    "sars-cov-2": "sars-cov-2",  # If available
    "rsv-a": "rsv-a",
    "rsv-b": "rsv-b",
    "mpox": "mpox",
    "hmpv": "hmpv",
    "marburg": "marburg",
    "measles": "measles",
    "ebola-zaire": "ebola-zaire",
    "ebola-sudan": "ebola-sudan",
    "west-nile": "west-nile",
}

# Metadata fields to retrieve from Pathoplexus
# These will be mapped to sonar-cli property names
PATHOPLEXUS_METADATA_FIELDS = [
    "accession",
    "accessionVersion",
    "sampleCollectionDate",
    "geoLocCountry",
    "geoLocAdmin1",
    "geoLocAdmin2",
    "hostNameScientific",
    "hostNameCommon",
    "authors",
    "ncbiReleaseDate",
    "insdcAccessionFull",
]

# Column mapping from Pathoplexus to sonar-cli
PATHOPLEXUS_COLUMN_MAPPING = {
    "accession": "name",  # Sample identifier
    "sampleCollectionDate": "collection_date",  # Collection date (needs normalization)
    "geoLocCountry": "country",  # Country
    "geoLocAdmin1": "region",  # Region/State
    "geoLocAdmin2": "location",  # City/Location
    "hostNameScientific": "host_scientific",  # Scientific host name
    "hostNameCommon": "host",  # Common host name
    "insdcAccessionFull": "insdc_accession",  # INSDC accession
}

# Fields that need special processing
PATHOPLEXUS_DATE_FIELDS = ["collection_date"]


class PathoplexusDatasetImporter(DatasetImporter):
    """
    Importer for Pathoplexus datasets via LAPIS API.
    """

    def __init__(
        self,
        pathogen: str,
        cache_dir: Optional[str] = None,
        sample_size: Optional[int] = None,
        aligned: bool = False,
        data_use_terms: str = "OPEN",
    ):
        """
        Initialize Pathoplexus dataset importer.

        Args:
            pathogen: Pathogen name (e.g., 'rsv-a', 'mpox')
            cache_dir: Directory for caching downloaded files
            sample_size: Number of samples to import. If None, import all.
            aligned: If True, download aligned sequences. If False, unaligned.
            data_use_terms: Filter by data use terms ('OPEN' or 'RESTRICTED')
        """
        super().__init__(
            pathogen=pathogen,
            cache_dir=cache_dir,
            sample_size=sample_size,
        )

        self.organism = PATHOGEN_TO_ORGANISM.get(pathogen.lower())
        if not self.organism:
            raise ValueError(
                f"Unsupported pathogen for Pathoplexus: {pathogen}. "
                f"Supported: {list(PATHOGEN_TO_ORGANISM.keys())}"
            )

        self.aligned = aligned
        self.data_use_terms = data_use_terms

    @property
    def source_name(self) -> str:
        return "pathoplexus"

    def _get_api_url(self, endpoint: str) -> str:
        """Construct API URL for the given endpoint."""
        return f"{LAPIS_BASE_URL}/{self.organism}/sample/{endpoint}"

    def _get_total_count(self) -> int:
        """Get total number of sequences available."""
        url = self._get_api_url("aggregated")
        params = {"dataUseTerms": self.data_use_terms}

        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("count", 0)
        return 0

    def _get_sample_accessions(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of accessions, optionally limited.

        Args:
            limit: Maximum number of accessions to return

        Returns:
            List of accession strings
        """
        url = self._get_api_url("details")
        params = {
            "dataUseTerms": self.data_use_terms,
            "fields": "accession",
        }

        LOGGER.info("Fetching accession list from Pathoplexus")
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        accessions = [item["accession"] for item in data.get("data", [])]
        # the accessions are contained all samples of this organism
        if limit and limit < len(accessions):
            random.seed(42)  # For reproducibility
            accessions = random.sample(accessions, limit)

            LOGGER.info(
                f"Sampled {limit} accessions from {len(data.get('data', []))} total"
            )
        return accessions

    def _download_metadata(self, accessions: Optional[List[str]] = None) -> List[Dict]:
        """
        Download metadata for sequences.

        Args:
            accessions: List of accessions to fetch. If None, fetch all.

        Returns:
            List of metadata dictionaries
        """
        url = self._get_api_url("details")
        params = {"dataUseTerms": self.data_use_terms}

        if accessions:
            # For large lists, we need to use POST
            if len(accessions) > 100:
                LOGGER.info(f"Fetching metadata for {len(accessions)} sequences (POST)")
                response = requests.post(
                    url,
                    json={"accession": accessions, "dataUseTerms": self.data_use_terms},
                )
            else:
                # Use GET with multiple accession params
                params["accession"] = accessions
                LOGGER.info(f"Fetching metadata for {len(accessions)} sequences (GET)")
                response = requests.get(url, params=params)
        else:
            LOGGER.info("Fetching all metadata")
            response = requests.get(url, params=params)

        response.raise_for_status()
        data = response.json()

        return data.get("data", [])

    def _download_sequences(
        self,
        output_path: Path,
        accessions: Optional[List[str]] = None,
    ) -> int:
        """
        Download sequences to a FASTA file.

        Args:
            output_path: Path to save FASTA file
            accessions: List of accessions to fetch. If None, fetch all.

        Returns:
            Number of sequences downloaded
        """
        endpoint = (
            "alignedNucleotideSequences"
            if self.aligned
            else "unalignedNucleotideSequences"
        )
        url = self._get_api_url(endpoint)

        params = {"dataUseTerms": self.data_use_terms}

        if accessions:
            if len(accessions) > 100:
                # Use POST for large requests
                LOGGER.info(f"Downloading {len(accessions)} sequences (POST)")
                response = requests.post(
                    url,
                    json={"accession": accessions, "dataUseTerms": self.data_use_terms},
                    stream=True,
                )
            else:
                params["accession"] = accessions
                LOGGER.info(f"Downloading {len(accessions)} sequences (GET)")
                response = requests.get(url, params=params, stream=True)
        else:
            LOGGER.info("Downloading all sequences")
            response = requests.get(url, params=params, stream=True)

        response.raise_for_status()

        # Write directly to file
        count = 0
        with open(output_path, "w") as f:
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    f.write(line + "\n")
                    if line.startswith(">"):
                        count += 1

        LOGGER.info(f"Downloaded {count} sequences to {output_path}")
        return count

    def download(self) -> Tuple[Path, Path]:
        """
        Download sequences and metadata from Pathoplexus.

        Returns:
            Tuple of (fasta_path, metadata_json_path)
        """
        # Determine accessions to download
        accessions = None
        if self.sample_size:
            total = self._get_total_count()
            LOGGER.info(f"Total sequences available: {total}")

            if self.sample_size < total:
                accessions = self._get_sample_accessions(self.sample_size)
            else:
                LOGGER.info("Sample size >= total, downloading all")

        # Download sequences
        fasta_path = self.cache_dir / f"{self.organism}_sequences.fasta"
        if not fasta_path.exists():
            self._download_sequences(fasta_path, accessions)
        else:
            LOGGER.info(f"Using cached sequences: {fasta_path}")

        # Download metadata
        metadata_path = self.cache_dir / f"{self.organism}_metadata.json"
        if not metadata_path.exists():
            metadata = self._download_metadata(accessions)
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            LOGGER.info(f"Saved metadata to {metadata_path}")
        else:
            LOGGER.info(f"Using cached metadata: {metadata_path}")

        return fasta_path, metadata_path

    def _transform_metadata(
        self,
        metadata_path: Path,
        output_path: Path,
    ) -> int:
        """
        Transform Pathoplexus metadata JSON to sonar-cli compatible TSV.

        Args:
            metadata_path: Path to metadata JSON file
            output_path: Path for output TSV file

        Returns:
            Number of rows written
        """
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Determine output columns
        output_columns = list(PATHOPLEXUS_COLUMN_MAPPING.values())
        # Add data_set field
        output_columns.append("data_set")

        count = 0
        processed_sample_ids = []

        with open(output_path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(
                f_out, fieldnames=output_columns, delimiter="\t", extrasaction="ignore"
            )
            writer.writeheader()

            for item in metadata:
                transformed = {}
                for pp_col, sonar_col in PATHOPLEXUS_COLUMN_MAPPING.items():
                    value = item.get(pp_col, "")
                    if value is not None and value != "":
                        value_str = str(value).strip()

                        # Normalize date fields
                        if sonar_col in PATHOPLEXUS_DATE_FIELDS:
                            value_str = normalize_date_format(value_str)

                        transformed[sonar_col] = value_str
                    # For empty values, only add the field if it's not a date field
                    elif sonar_col not in PATHOPLEXUS_DATE_FIELDS:
                        transformed[sonar_col] = ""

                # Add data_set field
                transformed["data_set"] = self.dataset_name

                # Store sample ID (name field)
                sample_id = transformed.get("name", "")
                if sample_id:
                    processed_sample_ids.append(sample_id)

                writer.writerow(transformed)
                count += 1

        # Write sample IDs to a separate file for future use (e.g., deletion)
        sample_id_file = output_path.parent / f"{self.dataset_name}_sampleID.txt"
        with open(sample_id_file, "w", encoding="utf-8") as f:
            for sid in processed_sample_ids:
                f.write(f"{sid}\n")

        LOGGER.info(f"Transformed {count} metadata rows to {output_path}")
        return count

    def preprocess(
        self,
        fasta_path: Path,
        metadata_path: Path,
    ) -> Tuple[Path, Path]:
        """
        Preprocess Pathoplexus dataset for import.

        Args:
            fasta_path: Path to downloaded FASTA file
            metadata_path: Path to downloaded metadata JSON file

        Returns:
            Tuple of (processed_fasta_path, processed_tsv_path)
        """
        processed_fasta = self.cache_dir / f"{self.dataset_name}.fasta"
        processed_tsv = self.cache_dir / f"{self.dataset_name}.tsv"

        # For Pathoplexus, sequences are already filtered during download
        # Just copy/rename the fasta file
        if not processed_fasta.exists():
            shutil.copy(fasta_path, processed_fasta)
            LOGGER.info(f"Copied FASTA to {processed_fasta}")

        # Transform metadata from JSON to TSV
        self._transform_metadata(metadata_path, processed_tsv)

        return processed_fasta, processed_tsv
