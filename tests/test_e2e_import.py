from pathlib import Path

import pytest

from .conftest import run_cli


@pytest.mark.run(order=1)
def test_parasail_no_anno_no_upload(monkeypatch, api_url, tmpfile_name):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 2 --fasta covid19/seqs.fasta.gz --cache {tmpfile_name}/parasail -t 2 --no-upload"
    code = run_cli(command)

    assert code == 0


@pytest.mark.run(order=2)
def test_mafft_no_anno_no_upload(monkeypatch, api_url, tmpfile_name):
    """Test import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 1 --fasta covid19/seqs.fasta.gz --cache {tmpfile_name}/mafft -t 2 --no-upload"
    code = run_cli(command)

    assert code == 0


def test_mafft_anno_prop(monkeypatch, api_url, tmpfile_name):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.map_unordered",
        lambda self, func, args=(), progress_bar=True, progress_bar_options={}, kwds={}, callback=None, error_callback=None: (
            func(arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 1 --fasta covid19/seqs.fasta.gz --cache {tmpfile_name}/mafft -t 2 --auto-anno --tsv covid19/meta.tsv --cols sample=IMS_ID collection_date=DATE_DRAW sequencing_tech=SEQ_REASON sample_type=SAMPLE_TYPE --auto-link"
    code = run_cli(command)

    assert code == 0
