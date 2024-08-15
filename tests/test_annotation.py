import os
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch

import pytest


def test_bcftools_merge_success(
    monkeypatch, annotator, accesion_SARSCOV2, tmpfile_name
):
    monkeypatch.chdir(Path(__file__).parent)

    input_vcfs = ["covid19/1.vcf", "covid19/2.vcf", "covid19/3.vcf"]
    output_vcf = os.path.join(tmpfile_name, "merged.vcf")

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0),  # bgzip sample1
            MagicMock(returncode=0),  # tabix sample1
            MagicMock(returncode=0),  # bgzip sample2
            MagicMock(returncode=0),  # tabix sample2
            MagicMock(returncode=0),  # bgzip sample3
            MagicMock(returncode=0),  # tabix sample3
            MagicMock(returncode=0),  # Merge command
        ]

        annotator.bcftools_merge(input_vcfs, output_vcf)

        assert mock_run.call_count == 7


# def test_bcftools_merge_fail(annotator):
#     input_vcfs = ["sample1.vcf", "sample2.vcf"]
#     output_vcf = "merged.vcf"
#     compressed_vcfs = ["sample1.vcf.gz", "sample2.vcf.gz"]

#     with patch("subprocess.run") as mock_run:
#         mock_run.side_effect = [
#             MagicMock(returncode=1),  # bgzip sample1
#         ]

#         annotator.bcftools_merge(input_vcfs, output_vcf)

#         assert annotator.sonar_cache.error_logfile_name == "error.log"


def test_snpeff_annotate_success(
    monkeypatch, annotator, accesion_SARSCOV2, tmpfile_name
):
    monkeypatch.chdir(Path(__file__).parent)
    input_vcf = "covid19/1.vcf"
    output_vcf = os.path.join(tmpfile_name, "output.anno.vcf")
    database_name = accesion_SARSCOV2

    with patch("builtins.open", mock_open()), patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        annotator.snpeff_annotate(input_vcf, output_vcf, database_name)


def test_snpeff_annotate_fail(monkeypatch, annotator, accesion_SARSCOV2, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)
    input_vcf = "covid19/1.vcf"
    output_vcf = os.path.join(tmpfile_name, "output.anno.vcf")
    database_name = accesion_SARSCOV2

    with patch("builtins.open", mock_open()), patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = b"Error"

        annotator.snpeff_annotate(None, output_vcf, database_name)

    annotator.annotator = None
    with pytest.raises(ValueError, match="Annotator executable path is not provided"):
        annotator.snpeff_annotate(input_vcf, output_vcf, database_name)


def test_bcftools_filter_success(
    monkeypatch, annotator, accesion_SARSCOV2, tmpfile_name
):
    monkeypatch.chdir(Path(__file__).parent)
    input_vcf = "covid19/1.vcf"
    output_vcf = os.path.join(tmpfile_name, "output.filtered.vcf")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        annotator.bcftools_filter(input_vcf, output_vcf)


# def test_bcftools_filter_fail(annotator):
#     input_vcf = "input.vcf"
#     output_vcf = "output.vcf"

#     with patch("subprocess.run") as mock_run:
#         mock_run.return_value.returncode = 1

#         annotator.bcftools_filter(input_vcf, output_vcf)

#         assert annotator.sonar_cache.error_logfile_name == "error.log"
