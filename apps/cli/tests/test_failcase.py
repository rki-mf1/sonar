import logging
from pathlib import Path

import pytest

from .conftest import run_cli


def test_match_no_ref(capfd, api_url):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        run_cli(f"match --db {api_url} -r NOREF")
    out, err = capfd.readouterr()
    lines = err.splitlines()
    assert "reference NOREF does not exist" in lines[-1]
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


@pytest.mark.xdist_group(name="hiv_group")
@pytest.mark.order(8)
def test_add_duplicated_ref(monkeypatch, capfd, api_url):
    """
    Test case to add a duplicated reference.
    NOTE: Right now, we allows adding a duplicated reference and updates it if it already exists
    """
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/HIV/NC_001802.1.gb"

    # Add the reference for the first time
    code = run_cli(f"add-ref --db {api_url} --gb {new_ref_file}")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0

    # Try to add the same reference again
    code = run_cli(f"add-ref --db {api_url} --gb {new_ref_file}")
    out, err = capfd.readouterr()
    assert (
        "successfully." in err
    )  # Assuming your CLI prints this message upon successful addition
    assert code == 0

    # Cleanup: delete the reference
    code = run_cli(f"delete-ref --db {api_url} -r NC_001802.1 --force")
    out, err = capfd.readouterr()
    assert "Reference deleted." in err
    assert code == 0


# add duplicated property
def test_add_prop_int(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name dup_integer --dtype value_integer --descr 'test-integer' "
    )
    out, err = capfd.readouterr()
    assert "Property added successfully" in err
    assert code == 0
    code = run_cli(
        f" add-prop --db {api_url} --name dup_integer --dtype value_integer --descr 'test-integer' "
    )
    out, err = capfd.readouterr()
    assert "Property already exists" in err
    assert code == 0

    code = run_cli(f"delete-prop --db {api_url} --name dup_integer --force ")
    out, err = capfd.readouterr()
    assert "successfully" in err
    assert code == 0


# delete non existing property name
def test_delete_fakeprop(capfd, api_url):
    code = run_cli(f" delete-prop --db {api_url} --name fakePROP --force ")
    out, err = capfd.readouterr()
    assert "No matching property found for deletion" in err
    assert code == 0


def test_delete_sample(monkeypatch, capfd, api_url):
    code = run_cli(f"delete-sample --db {api_url} --sample fake-id --force")
    out, err = capfd.readouterr()
    assert "0 of 1 samples found and deleted." in err
    assert code == 0


# delete non existing sequence
def test_delete_sequence(monkeypatch, capfd, api_url):
    code = run_cli(f"delete-sequence --db {api_url} --sequence fake-id --force")
    out, err = capfd.readouterr()
    print(out, err, code)
    assert "0 of 1 sequences found and deleted." in err
    assert code == 0


# delete non existing reference
def test_delete_noref(capfd, api_url):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        run_cli(f"delete-ref --db {api_url} -r fakeREFID --force")
    out, err = capfd.readouterr()
    assert "The reference fakeREFID does not exist." in err
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


# file not found
def test_match_no_fasta(caplog, api_url):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        with caplog.at_level(logging.ERROR):
            run_cli(f"import --db {api_url} -r MN908947.3 --fasta where.is.my.fasta")
    assert "The file 'where.is.my.fasta' does not exist" in caplog.text
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


def test_match_no_tsv(caplog, api_url):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        with caplog.at_level(logging.ERROR):
            run_cli(f"import --db {api_url} -r MN908947.3 --tsv where.is.my.tsv")

    assert "The file 'where.is.my.tsv' does not exist" in caplog.text
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


def test_match_no_gb(caplog, api_url):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        with caplog.at_level(logging.ERROR):
            run_cli(f"add-ref --db {api_url} --gb where.is.gb.gb")
    assert "The file 'where.is.gb.gb' does not exist" in caplog.text
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
