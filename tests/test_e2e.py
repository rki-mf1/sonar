import os
from pathlib import Path

import pytest

from .conftest import run_cli


def test_help():
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        run_cli("--help")
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0


def test_version():
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        run_cli("-v")
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0


def test_get_list_prop(capfd, api_url):
    code = run_cli(f" list-prop --db {api_url} ")
    out, err = capfd.readouterr()
    assert "name" in out
    assert code == 0


def test_get_list_ref(capfd, api_url):
    code = run_cli(f" list-ref --db {api_url} ")
    out, err = capfd.readouterr()
    assert "accession" in out
    assert code == 0


@pytest.mark.run(order=1)
def test_add_prop_varchar(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_varchar --dtype value_varchar --descr 'test-varchar' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0


@pytest.mark.run(order=2)
def test_add_prop_int(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_integer --dtype value_integer --descr 'test-integer' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0


@pytest.mark.run(order=3)
def test_add_prop_float(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_float --dtype value_float --descr 'test-floating-point-number' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0


@pytest.mark.run(order=4)
def test_add_prop_text(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_text --dtype value_text --descr 'test-text' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0


@pytest.mark.run(order=5)
def test_add_prop_zip(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_zip --dtype value_zip --descr 'test-zip' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0


@pytest.mark.run(order=6)
def test_add_prop_date(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_date --dtype value_date --descr 'test-date' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0


@pytest.mark.run(order=7)
def test_delete_prop(capfd, api_url):
    code = run_cli(f" delete-prop --db {api_url} --name test_varchar --force ")
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0

    code = run_cli(f" delete-prop --db {api_url} --name test_integer --force ")
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0

    code = run_cli(f" delete-prop --db {api_url} --name test_float --force ")
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0

    code = run_cli(f" delete-prop --db {api_url} --name test_text --force ")
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0

    code = run_cli(f" delete-prop --db {api_url} --name test_zip --force ")
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0

    code = run_cli(f" delete-prop --db {api_url} --name test_date --force ")
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0


def test_parasail_no_upload(monkeypatch, api_url, tmpfile_name):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)
    command = f"import --db {api_url} -r MN908947.3 --method 2 --fasta covid19/seqs.fasta.gz --cache {tmpfile_name}/parasail  -t 2 --no-upload"
    code = run_cli(command)

    assert code == 0


def test_mafft_no_upload(monkeypatch, api_url, tmpfile_name):
    """Test import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    command = f"import --db {api_url} -r MN908947.3 --method 1 --fasta covid19/seqs.fasta.gz --cache {tmpfile_name}/mafft  -t 2 --no-upload"
    code = run_cli(command)

    assert code == 0


# pytest fail to work with  workerpool shared_objects
def skip_test_add_sequence_parasail_auto_anno(monkeypatch, api_url, tmpfile_name):
    """Test import command using covid19 compressed fasta file and perform annotation"""
    monkeypatch.chdir(Path(__file__).parent)
    command = f"import --db {api_url} -r MN908947.3 --method 2 --fasta covid19/seqs.fasta.gz --cache {tmpfile_name}  -t 2 --auto-anno --update"
    code = run_cli(command)

    assert code == 0


# pytest fail to work with  workerpool shared_objects
def skip_test_add_sequence_mafft_prop_auto_link(monkeypatch, api_url, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)
    code = run_cli(
        f"import --db {api_url} -r MN908947.3 --method 1 --fasta covid19/seqs.fasta.gz  --tsv covid19/meta.tsv --cache {tmpfile_name}  --cols sample=IMS_ID -t 1 --auto-link --update"
    )
    assert code == 0


def test_add_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    # new_ref_file = "mpox/NC_063383.1.gb"
    new_ref_file = "influenza/InfluA_H7N9_seg6.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in out
    assert code == 0


def test_delete_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    code = run_cli(f" delete-ref --db {api_url} -r NC_026429.1  --force")
    out, err = capfd.readouterr()
    assert "Reference deleted." in out
    assert code == 0


def skip_test_delete_sample():
    pass


def test_output_csv_format(capfd, api_url, tmpfile_name):

    code = run_cli(
        f" match --db {api_url} -r MN908947.3 --profile S:N440K C24503T --format csv -o {tmpfile_name}/out.csv "
    )
    out, err = capfd.readouterr()
    assert os.path.exists(f"{tmpfile_name}/out.csv") is True
    assert code == 0
