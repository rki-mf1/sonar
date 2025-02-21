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


@pytest.mark.xdist_group(name="group_prop")
@pytest.mark.order(1)
def test_add_prop_varchar(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_varchar --dtype value_varchar --descr 'test-varchar' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0


@pytest.mark.xdist_group(name="group_prop")
@pytest.mark.order(2)
def test_add_prop_int(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_integer --dtype value_integer --descr 'test-integer' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0


@pytest.mark.xdist_group(name="group_prop")
@pytest.mark.order(3)
def test_add_prop_float(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_float --dtype value_float --descr 'test-floating-point-number' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0


@pytest.mark.xdist_group(name="group_prop")
@pytest.mark.order(4)
def test_add_prop_text(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_text --dtype value_text --descr 'test-text' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0


@pytest.mark.xdist_group(name="group_prop")
@pytest.mark.order(5)
def test_add_prop_zip(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_zip --dtype value_zip --descr 'test-zip' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0


@pytest.mark.xdist_group(name="group_prop")
@pytest.mark.order(6)
def test_add_prop_date(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_date --dtype value_date --descr 'test-date' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0


@pytest.mark.xdist_group(name="group_prop")
@pytest.mark.order(8)
def test_delete_prop_varchar(capfd, api_url):
    code = run_cli(f" delete-prop --db {api_url} --name test_varchar --force ")
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0

    code = run_cli(f" delete-prop --db {api_url} --name test_integer --force ")
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0

    code = run_cli(f" delete-prop --db {api_url} --name test_float --force ")
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0

    code = run_cli(f" delete-prop --db {api_url} --name test_text --force ")
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0

    code = run_cli(f" delete-prop --db {api_url} --name test_zip --force ")
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0

    code = run_cli(f" delete-prop --db {api_url} --name test_date --force ")
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0


def test_add_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/influenza/InfluA_H7N9_seg6.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


def test_delete_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    code = run_cli(f" delete-ref --db {api_url} -r NC_026429.1  --force")
    out, err = capfd.readouterr()
    assert "Reference deleted." in err
    assert code == 0


def test_delete_sample_fromfile(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    code = run_cli(
        f"delete-sample --db {api_url} --sample-file sars-cov-2/sample_list.2.txt --force"
    )
    out, err = capfd.readouterr()
    assert "0 of 2 samples found and deleted." in err
    assert code == 0


def test_output_csv_format(capfd, api_url, tmpfile_name):

    code = run_cli(
        f" match --db {api_url} -r MN908947.3 --profile S:N440K C24503T --format csv -o {tmpfile_name}/out.csv "
    )
    assert os.path.exists(f"{tmpfile_name}/out.csv") is True
    assert code == 0
