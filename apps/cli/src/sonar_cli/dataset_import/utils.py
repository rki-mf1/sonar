"""
Utility functions for dataset import operations.
"""

import gzip
import lzma
from pathlib import Path
import random
import shutil
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Set
from typing import Tuple

import requests
from sonar_cli.logging import LoggingConfigurator
from tqdm import tqdm

LOGGER = LoggingConfigurator.get_logger()

# Chunk size for downloading large files (1MB)
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


def download_file(
    url: str,
    output_path: Path,
    description: Optional[str] = None,
    show_progress: bool = True,
) -> Path:
    """
    Download a file from URL with progress bar.

    Args:
        url: URL to download from
        output_path: Path to save the downloaded file
        description: Description for progress bar
        show_progress: Whether to show progress bar

    Returns:
        Path to the downloaded file
    """
    LOGGER.info(f"Downloading from {url}")

    response = requests.get(url, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))

    with open(output_path, "wb") as f:
        if show_progress and total_size > 0:
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=description or output_path.name,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        else:
            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                if chunk:
                    f.write(chunk)

    LOGGER.info(f"Downloaded to {output_path}")
    return output_path


def decompress_xz(input_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Decompress an .xz file.

    Args:
        input_path: Path to the .xz file
        output_path: Path for decompressed file. If None, removes .xz extension.

    Returns:
        Path to the decompressed file
    """
    if output_path is None:
        output_path = input_path.with_suffix("")

    LOGGER.info(f"Decompressing {input_path}")

    with lzma.open(input_path, "rb") as f_in:
        with open(output_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    LOGGER.info(f"Decompressed to {output_path}")
    return output_path


def decompress_gz(input_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Decompress a .gz file.

    Args:
        input_path: Path to the .gz file
        output_path: Path for decompressed file. If None, removes .gz extension.

    Returns:
        Path to the decompressed file
    """
    if output_path is None:
        output_path = input_path.with_suffix("")

    LOGGER.info(f"Decompressing {input_path}")

    with gzip.open(input_path, "rb") as f_in:
        with open(output_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    LOGGER.info(f"Decompressed to {output_path}")
    return output_path


def parse_fasta(fasta_path: Path) -> Iterator[Tuple[str, str]]:
    """
    Parse a FASTA file and yield (header, sequence) tuples.

    Args:
        fasta_path: Path to FASTA file

    Yields:
        Tuple of (header without '>', sequence)
    """
    header = None
    sequence_parts = []

    with open(fasta_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(sequence_parts)
                header = line[1:]  # Remove '>'
                sequence_parts = []
            else:
                sequence_parts.append(line)

        # Yield the last sequence
        if header is not None:
            yield header, "".join(sequence_parts)


def write_fasta(
    sequences: Iterator[Tuple[str, str]],
    output_path: Path,
    line_width: int = 80,
) -> int:
    """
    Write sequences to a FASTA file.

    Args:
        sequences: Iterator of (header, sequence) tuples
        output_path: Path to output FASTA file
        line_width: Maximum line width for sequences (0 for no wrapping)

    Returns:
        Number of sequences written
    """
    count = 0
    with open(output_path, "w") as f:
        for header, sequence in sequences:
            f.write(f">{header}\n")
            if line_width > 0:
                for i in range(0, len(sequence), line_width):
                    f.write(sequence[i : i + line_width] + "\n")
            else:
                f.write(sequence + "\n")
            count += 1
    return count


def subsample_fasta(
    fasta_path: Path,
    output_path: Path,
    sample_size: int,
    seed: int = 42,
) -> Set[str]:
    """
    Randomly subsample sequences from a FASTA file.

    Args:
        fasta_path: Path to input FASTA file
        output_path: Path to output FASTA file
        sample_size: Number of sequences to sample
        seed: Random seed for reproducibility

    Returns:
        Set of sampled sequence IDs (first part of header before space)
    """
    LOGGER.info(f"Counting sequences in {fasta_path}")

    # First pass: count sequences and collect headers
    headers = []
    for header, _ in parse_fasta(fasta_path):
        headers.append(header)

    total_count = len(headers)
    LOGGER.info(f"Total sequences: {total_count}")

    if sample_size >= total_count:
        LOGGER.info("Sample size >= total, copying all sequences")
        shutil.copy(fasta_path, output_path)
        return {h.split()[0] for h in headers}

    # Random sampling
    random.seed(seed)
    sampled_headers = set(random.sample(headers, sample_size))
    sampled_ids = {h.split()[0] for h in sampled_headers}

    LOGGER.info(f"Sampling {sample_size} sequences")

    # Second pass: write sampled sequences
    def sampled_sequences():
        for header, sequence in parse_fasta(fasta_path):
            if header in sampled_headers:
                yield header, sequence

    count = write_fasta(sampled_sequences(), output_path)
    LOGGER.info(f"Wrote {count} sequences to {output_path}")

    return sampled_ids


def filter_tsv_by_ids(
    tsv_path: Path,
    output_path: Path,
    ids: Set[str],
    id_column: str = "name",
    delimiter: str = "\t",
) -> int:
    """
    Filter a TSV file to only include rows with IDs in the given set.

    Args:
        tsv_path: Path to input TSV file
        output_path: Path to output TSV file
        ids: Set of IDs to keep
        id_column: Name of the column containing the ID
        delimiter: Column delimiter

    Returns:
        Number of rows written (excluding header)
    """
    import csv

    count = 0
    with open(tsv_path, "r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in, delimiter=delimiter)

        with open(output_path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(
                f_out, fieldnames=reader.fieldnames, delimiter=delimiter
            )
            writer.writeheader()

            for row in reader:
                if row.get(id_column) in ids:
                    writer.writerow(row)
                    count += 1

    LOGGER.info(f"Filtered {count} rows to {output_path}")
    return count


def get_zenodo_latest_files(concept_doi: str) -> Dict[str, str]:
    """
    Get download URLs for files in the latest version of a Zenodo record.

    Args:
        concept_doi: The concept DOI (e.g., "10.5281/zenodo.5139363")

    Returns:
        Dict mapping filename to download URL
    """
    # Get the latest record
    api_url = (
        f"https://zenodo.org/api/records?q=conceptdoi:{concept_doi}&all_versions=false"
    )

    LOGGER.info(f"Fetching Zenodo record for {concept_doi}")
    response = requests.get(api_url)
    response.raise_for_status()

    data = response.json()
    if not data.get("hits", {}).get("hits"):
        raise ValueError(f"No records found for DOI: {concept_doi}")

    record = data["hits"]["hits"][0]
    files = record.get("files", [])

    return {f["key"]: f["links"]["self"] for f in files}


def get_zenodo_record_files(record_id: str) -> Dict[str, str]:
    """
    Get download URLs for files in a specific Zenodo record.

    Args:
        record_id: The Zenodo record ID (e.g., "17964898")

    Returns:
        Dict mapping filename to download URL
    """
    api_url = f"https://zenodo.org/api/records/{record_id}"

    LOGGER.info(f"Fetching Zenodo record {record_id}")
    response = requests.get(api_url)
    response.raise_for_status()

    record = response.json()
    files = record.get("files", [])

    return {f["key"]: f["links"]["self"] for f in files}
