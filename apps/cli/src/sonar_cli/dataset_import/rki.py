"""
RKI SARS-CoV-2 Dataset Importer.

Downloads and processes SARS-CoV-2 sequence data from the Robert Koch Institute,
published on Zenodo.

Data source: https://github.com/robert-koch-institut/SARS-CoV-2-Sequenzdaten_aus_Deutschland
Zenodo: https://doi.org/10.5281/zenodo.5139363
"""

import csv
from pathlib import Path
from typing import Dict
from typing import Optional
from typing import Set
from typing import Tuple

from .base import DatasetImporter
from .utils import decompress_xz
from .utils import download_file
from .utils import get_zenodo_record_files
from .utils import LOGGER
from .utils import parse_fasta
from .utils import subsample_fasta
from .utils import write_fasta


# Zenodo concept DOI for RKI SARS-CoV-2 data (all versions)
RKI_ZENODO_CONCEPT_DOI = "10.5281/zenodo.5139363"

# Latest known record ID (will be updated dynamically)
RKI_ZENODO_LATEST_RECORD = "17964898"

# Expected file names in the Zenodo record
RKI_FASTA_FILENAME = "SARS-CoV-2-Sequenzdaten_Deutschland.fasta.xz"
RKI_TSV_FILENAME = "SARS-CoV-2-Sequenzdaten_Deutschland.tsv.xz"

# Column mappings from RKI TSV to sonar-cli expected format
# RKI column name -> sonar property name
RKI_COLUMN_MAPPING = {
    "ID": "name",  # Sample identifier
    "DATE_OF_SAMPLING": "collection_date",  # Collection date (sampling date)
    "SEQUENCING_METHOD": "sequencing_tech",  # Sequencing technology
    "DL.POSTAL_CODE": "zip_code",  # ZIP code (Diagnostic Lab postal code)
    "LINEAGE_LATEST": "lineage",  # Pangolin lineage (latest)
}

# Additional fields that will be added with fixed values
RKI_FIXED_FIELDS = {
    "country": "Germany",  # All RKI data is from Germany
    "host": "Human",  # RKI data is human samples
    "data_set": None,  # Will be set to dataset_name (e.g., "rki_sars-cov-2")
}

# Optional fields that may exist in RKI data but are not in standard properties
RKI_OPTIONAL_FIELDS = {
    "POSTAL_CODE": "sequencing_lab_pc",  # Sequencing lab postal code
    "SEQUENCE.SEQUENCING_REASON": "seq_reason",  # Sequencing reason
    "SEQUENCE.SAMPLE_TYPE": "sample_type",  # Sample type
    "SEQUENCE.SEQUENCING_LAB_SAMPLE_ID": "lab_sample_id",  # Lab sample ID
    "PANGOLIN.PANGOLIN_VERSION_LATEST": "pangolin_version",  # Pangolin version
}


class RKIDatasetImporter(DatasetImporter):
    """
    Importer for RKI SARS-CoV-2 dataset from Zenodo.
    """

    def __init__(
        self,
        pathogen: str = "sars-cov-2",
        cache_dir: Optional[str] = None,
        sample_size: Optional[int] = None,
        record_id: Optional[str] = None,
    ):
        """
        Initialize RKI dataset importer.

        Args:
            pathogen: Must be 'sars-cov-2' for RKI data
            cache_dir: Directory for caching downloaded files
            sample_size: Number of samples to import. If None, import all.
            record_id: Specific Zenodo record ID. If None, uses latest known.
        """
        if pathogen.lower() != "sars-cov-2":
            raise ValueError("RKI dataset only supports 'sars-cov-2' pathogen")

        super().__init__(
            pathogen=pathogen,
            cache_dir=cache_dir,
            sample_size=sample_size,
        )

        self.record_id = record_id or RKI_ZENODO_LATEST_RECORD

    @property
    def source_name(self) -> str:
        return "rki"

    def _get_download_urls(self) -> Dict[str, str]:
        """Get download URLs for the required files from Zenodo."""
        return get_zenodo_record_files(self.record_id)

    def download(self) -> Tuple[Path, Path]:
        """
        Download FASTA and TSV files from Zenodo.

        Returns:
            Tuple of (fasta_path, tsv_path) pointing to decompressed files
        """
        # Get file URLs
        file_urls = self._get_download_urls()

        # Check required files exist
        if RKI_FASTA_FILENAME not in file_urls:
            raise ValueError(
                f"FASTA file not found in Zenodo record: {RKI_FASTA_FILENAME}"
            )
        if RKI_TSV_FILENAME not in file_urls:
            raise ValueError(f"TSV file not found in Zenodo record: {RKI_TSV_FILENAME}")

        # Download FASTA
        fasta_xz_path = self.cache_dir / RKI_FASTA_FILENAME
        if not fasta_xz_path.exists():
            download_file(
                file_urls[RKI_FASTA_FILENAME],
                fasta_xz_path,
                description="Downloading FASTA",
            )
        else:
            LOGGER.info(f"Using cached FASTA: {fasta_xz_path}")

        # Download TSV
        tsv_xz_path = self.cache_dir / RKI_TSV_FILENAME
        if not tsv_xz_path.exists():
            download_file(
                file_urls[RKI_TSV_FILENAME],
                tsv_xz_path,
                description="Downloading TSV",
            )
        else:
            LOGGER.info(f"Using cached TSV: {tsv_xz_path}")

        # Decompress files
        fasta_path = self.cache_dir / "SARS-CoV-2-Sequenzdaten_Deutschland.fasta"
        tsv_path = self.cache_dir / "SARS-CoV-2-Sequenzdaten_Deutschland.tsv"

        if not fasta_path.exists():
            decompress_xz(fasta_xz_path, fasta_path)
        else:
            LOGGER.info(f"Using cached decompressed FASTA: {fasta_path}")

        if not tsv_path.exists():
            decompress_xz(tsv_xz_path, tsv_path)
        else:
            LOGGER.info(f"Using cached decompressed TSV: {tsv_path}")

        return fasta_path, tsv_path

    def _transform_metadata(
        self,
        input_path: Path,
        output_path: Path,
        sample_ids: Optional[Set[str]] = None,
    ) -> int:
        """
        Transform RKI TSV to sonar-cli compatible format.

        Args:
            input_path: Path to RKI TSV file
            output_path: Path for output TSV file
            sample_ids: If provided, only include these sample IDs

        Returns:
            Number of rows written
        """
        count = 0
        processed_sample_ids = []

        # Determine output columns (standard + fixed fields)
        output_columns = list(RKI_COLUMN_MAPPING.values())
        output_columns.extend(RKI_FIXED_FIELDS.keys())

        # Add optional fields if they exist in the input
        output_columns.extend(RKI_OPTIONAL_FIELDS.values())

        with open(input_path, "r", newline="", encoding="utf-8") as f_in:
            reader = csv.DictReader(f_in, delimiter="\t")

            with open(output_path, "w", newline="", encoding="utf-8") as f_out:
                writer = csv.DictWriter(
                    f_out,
                    fieldnames=output_columns,
                    delimiter="\t",
                    extrasaction="ignore",
                )
                writer.writeheader()

                for row in reader:
                    # Get sample ID (ID column in RKI data)
                    sample_id = row.get("ID", "")

                    # Filter by sample_ids if provided
                    if sample_ids is not None and sample_id not in sample_ids:
                        continue

                    # Transform row with standard mappings
                    transformed = {}
                    for rki_col, sonar_col in RKI_COLUMN_MAPPING.items():
                        value = row.get(rki_col, "")
                        # Clean up the value
                        if value and value.strip():
                            transformed[sonar_col] = value.strip()
                        else:
                            transformed[sonar_col] = ""

                    # Add fixed fields
                    for field, value in RKI_FIXED_FIELDS.items():
                        if field == "data_set":
                            # Set data_set to the dataset name
                            transformed[field] = self.dataset_name
                        else:
                            transformed[field] = value

                    # Add optional fields if they exist
                    for rki_col, sonar_col in RKI_OPTIONAL_FIELDS.items():
                        value = row.get(rki_col, "")
                        if value and value.strip():
                            transformed[sonar_col] = value.strip()
                        else:
                            transformed[sonar_col] = ""

                    writer.writerow(transformed)
                    processed_sample_ids.append(sample_id)
                    count += 1

        # Write sample IDs to a separate file for future use (e.g., deletion)
        sample_id_file = output_path.parent / f"{self.dataset_name}_sampleID.txt"
        with open(sample_id_file, "w", encoding="utf-8") as f:
            for sid in processed_sample_ids:
                f.write(f"{sid}\n")

        LOGGER.info(f"Transformed {count} metadata rows to {output_path}")
        return count

    def _extract_sample_id_from_header(self, header: str) -> str:
        """
        Extract sample ID from FASTA header.

        RKI FASTA headers are typically just the ID (sample identifier).
        """
        return header.split()[0]

    def preprocess(
        self,
        fasta_path: Path,
        metadata_path: Path,
    ) -> Tuple[Path, Path]:
        """
        Preprocess RKI dataset for import.

        Args:
            fasta_path: Path to decompressed FASTA file
            metadata_path: Path to decompressed TSV file

        Returns:
            Tuple of (processed_fasta_path, processed_tsv_path)
        """
        processed_fasta = self.cache_dir / f"{self.dataset_name}.fasta"
        processed_tsv = self.cache_dir / f"{self.dataset_name}.tsv"

        sample_ids = None

        # Subsample if needed
        if self.sample_size:
            LOGGER.info(f"Subsampling {self.sample_size} sequences")
            sample_ids = subsample_fasta(
                fasta_path,
                processed_fasta,
                self.sample_size,
            )
        else:
            # Copy all sequences (just create a symlink or copy)
            LOGGER.info("Using all sequences (no subsampling)")
            if not processed_fasta.exists():
                # Read and write to ensure consistent format
                count = 0

                def all_sequences():
                    nonlocal count
                    for header, seq in parse_fasta(fasta_path):
                        count += 1
                        yield header, seq

                write_fasta(all_sequences(), processed_fasta)
                LOGGER.info(f"Copied {count} sequences")

                # Collect all IDs for metadata filtering
                sample_ids = set()
                for header, _ in parse_fasta(processed_fasta):
                    sample_ids.add(self._extract_sample_id_from_header(header))

        # Transform metadata
        self._transform_metadata(metadata_path, processed_tsv, sample_ids)

        return processed_fasta, processed_tsv
