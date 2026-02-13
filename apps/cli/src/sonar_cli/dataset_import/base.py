"""
Base class for dataset importers.

This module defines the abstract base class that all dataset importers
must inherit from, ensuring a consistent interface across different data sources.
"""

from abc import ABC
from abc import abstractmethod
from pathlib import Path
import tempfile
from typing import Optional
from typing import Tuple

from sonar_cli.logging import LoggingConfigurator

LOGGER = LoggingConfigurator.get_logger()


class DatasetImporter(ABC):
    """
    Abstract base class for dataset importers.

    All dataset importers must implement the download, preprocess, and import methods.
    """

    def __init__(
        self,
        pathogen: str,
        cache_dir: Optional[str] = None,
        sample_size: Optional[int] = None,
    ):
        """
        Initialize the dataset importer.

        Args:
            pathogen: Name of the pathogen to import
            cache_dir: Directory for caching downloaded files. If None, a temp dir is used.
            sample_size: Number of samples to import. If None, import all.
        """
        self.pathogen = pathogen.lower()
        self.sample_size = sample_size

        # Set up cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._temp_dir = None
        else:
            self._temp_dir = tempfile.TemporaryDirectory()
            self.cache_dir = Path(self._temp_dir.name)

        LOGGER.info(f"Using cache directory: {self.cache_dir}")

    def __del__(self):
        """Clean up temporary directory if created."""
        if self._temp_dir:
            try:
                self._temp_dir.cleanup()
            except Exception:
                pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the data source."""
        pass

    @property
    def dataset_name(self) -> str:
        """Generate dataset name in format: {source}_{pathogen}."""
        return f"{self.source_name}_{self.pathogen}"

    @abstractmethod
    def download(self) -> Tuple[Path, Path]:
        """
        Download the dataset files.

        Returns:
            Tuple of (fasta_path, metadata_path) pointing to downloaded files
        """
        pass

    @abstractmethod
    def preprocess(self, fasta_path: Path, metadata_path: Path) -> Tuple[Path, Path]:
        """
        Preprocess the downloaded files for import.

        This includes:
        - Subsampling if sample_size is specified
        - Reformatting metadata to match sonar-cli expectations
        - Any source-specific transformations

        Args:
            fasta_path: Path to downloaded FASTA file
            metadata_path: Path to downloaded metadata file

        Returns:
            Tuple of (processed_fasta_path, processed_metadata_path)
        """
        pass

    def run(self) -> Tuple[Path, Path]:
        """
        Execute the full import pipeline.

        Returns:
            Tuple of (fasta_path, tsv_path) ready for sonar-cli import
        """
        LOGGER.info(f"Starting dataset import from {self.source_name}")
        LOGGER.info(f"Pathogen: {self.pathogen}")
        LOGGER.info(f"Sample size: {self.sample_size if self.sample_size else 'all'}")

        # Download
        LOGGER.info("Downloading dataset...")
        fasta_path, metadata_path = self.download()
        LOGGER.info(f"Downloaded FASTA: {fasta_path}")
        LOGGER.info(f"Downloaded metadata: {metadata_path}")

        # Preprocess
        LOGGER.info("Preprocessing dataset...")
        processed_fasta, processed_tsv = self.preprocess(fasta_path, metadata_path)
        LOGGER.info(f"Processed FASTA: {processed_fasta}")
        LOGGER.info(f"Processed TSV: {processed_tsv}")

        return processed_fasta, processed_tsv
