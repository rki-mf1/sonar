from pathlib import Path

import pytest

from .conftest import run_cli


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(1)
def test_add_cov19_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/covid19/MN908947.nextclade.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(2)
def test_parasail_no_anno_no_upload(monkeypatch, api_url, tmpfile_name):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 2 --fasta ../../../test-data/covid19/seqs.fasta.gz --cache {tmpfile_name}/parasail -t 2 --no-upload"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(3)
def test_mafft_no_anno_no_upload(monkeypatch, api_url, tmpfile_name):
    """Test import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/covid19/seqs.fasta.gz --cache {tmpfile_name}/mafft -t 2 --no-upload"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(4)
def test_add_sequence_mafft_anno_prop(monkeypatch, api_url, tmpfile_name):
    """Test import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    # monkeypatch.setattr(
    #     "mpire.WorkerPool.map_unordered",
    #     lambda self, func, args=(), progress_bar=True, progress_bar_options={}, kwds={}, callback=None, error_callback=None: (
    #         func(** arg) for arg in args
    #     ),
    # )
    command = f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/covid19/seqs.fasta.gz --cache {tmpfile_name}/mafft -t 2 --auto-anno --tsv covid19/meta.tsv --cols name=IMS_ID collection_date=DATE_DRAW sequencing_tech=SEQ_REASON sample_type=SAMPLE_TYPE "
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(5)
def test_add_sequence_mafft_no_skip(monkeypatch, api_url, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    code = run_cli(
        f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/covid19/seqs.fasta.gz  --cache {tmpfile_name}/mafft  --no-skip --no-upload"
    )
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(6)
def test_add_sequence_mafft_skip(monkeypatch, api_url, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    code = run_cli(
        f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/covid19/seqs.fasta.gz --cache {tmpfile_name}/mafft -t 1 --no-upload"
    )
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(7)
def test_wfa_anno_no_upload(monkeypatch, api_url, tmpfile_name):
    """Test import command using wfa method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 3 --fasta ../../../test-data/covid19/seqs.fasta.gz --cache {tmpfile_name}/wfa -t 2 --no-upload"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(8)
def test_add_prop_autolink(monkeypatch, api_url, tmpfile_name):
    """Test import command using autolink"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.map_unordered",
        lambda self, func, args=(), progress_bar=True, progress_bar_options={}, kwds={}, callback=None, error_callback=None: (
            func(arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 1 --cache {tmpfile_name}/mafft -t 1  --tsv covid19/meta.tsv --cols name=IMS_ID --auto-link"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(9)
def test_add_prop(monkeypatch, api_url, tmpfile_name):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.map_unordered",
        lambda self, func, args=(), progress_bar=True, progress_bar_options={}, kwds={}, callback=None, error_callback=None: (
            func(arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 1 --cache {tmpfile_name}/mafft -t 2  --tsv covid19/meta.tsv --cols name=IMS_ID collection_date=DATE_DRAW sequencing_tech=SEQ_REASON sample_type=SAMPLE_TYPE"
    code = run_cli(command)

    assert code == 0
