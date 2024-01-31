import re

import pytest
from sonar_cli import sonar


def split_cli(s):
    """Split a string into a list of individual arguments, respecting quotes"""
    return re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*")+', s)


def run_cli(s):
    """Helper function to simulate running the command line ./sonar <args>"""
    return sonar.main(sonar.parse_args(split_cli(s)))


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


def test_add_prop(capfd, api_url):
    code = run_cli(
        f" add-prop --db {api_url} --name test_prop --dtype value_integer --descr 'test-information' "
    )
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0


def test_delete_prop(capfd, api_url):
    code = run_cli(f" delete-prop --db {api_url} --name test_prop --force ")
    out, err = capfd.readouterr()
    assert "successfully" in out
    assert code == 0
