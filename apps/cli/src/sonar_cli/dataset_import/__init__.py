"""
Dataset Import Module for sonar-cli.

This module provides functionality to download and import public pathogen
genomics datasets from various sources.

Supported sources:
- RKI: Robert Koch Institute SARS-CoV-2 data from Germany (Zenodo)
- Pathoplexus: Various pathogens (RSV-A, RSV-B, Mpox, HMPV, etc.)
"""

from .base import DatasetImporter
from .pathoplexus import PathoplexusDatasetImporter
from .rki import RKIDatasetImporter

__all__ = [
    "DatasetImporter",
    "RKIDatasetImporter",
    "PathoplexusDatasetImporter",
]

# Registry of available data sources
DATASET_SOURCES = {
    "rki": RKIDatasetImporter,
    "pathoplexus": PathoplexusDatasetImporter,
}

# Supported pathogens per source
SUPPORTED_PATHOGENS = {
    "rki": ["sars-cov-2"],
    "pathoplexus": [
        "sars-cov-2",
        "rsv-a",
        "rsv-b",
        "mpox",
        "hmpv",
        "marburg",
        "measles",
        "ebola-zaire",
        "ebola-sudan",
        "west-nile",
    ],
}


def get_importer(source: str, pathogen: str, **kwargs):
    """
    Factory function to get the appropriate dataset importer.

    Args:
        source: Data source name (e.g., 'rki', 'pathoplexus')
        pathogen: Pathogen name (e.g., 'sars-cov-2', 'rsv-a')
        **kwargs: Additional arguments passed to the importer

    Returns:
        DatasetImporter: An instance of the appropriate importer class

    Raises:
        ValueError: If source or pathogen is not supported
    """
    source = source.lower()
    pathogen = pathogen.lower()

    if source not in DATASET_SOURCES:
        raise ValueError(
            f"Unknown data source: {source}. "
            f"Supported sources: {list(DATASET_SOURCES.keys())}"
        )

    if pathogen not in SUPPORTED_PATHOGENS.get(source, []):
        raise ValueError(
            f"Pathogen '{pathogen}' is not supported for source '{source}'. "
            f"Supported pathogens: {SUPPORTED_PATHOGENS[source]}"
        )

    importer_class = DATASET_SOURCES[source]
    return importer_class(pathogen=pathogen, **kwargs)


# # RKI SARS-CoV-2 (ข้อมูลจาก Germany)
# sonar-cli import-dataset --source rki --pathogen sars-cov-2 -r MN908947.3 --sample-size 1000

# # Pathoplexus RSV-B
# sonar-cli import-dataset --source pathoplexus --pathogen rsv-b -r <your-reference> --sample-size 500

# # Download เท่านั้น (ไม่ import) ??
# sonar-cli import-dataset --source rki --pathogen sars-cov-2 --sample-size 100 --download-only --cache ./my_cache

# # Import ทั้งหมด
# sonar-cli import-dataset --source pathoplexus --pathogen mpox -r <ref> --method wfa --threads 8
