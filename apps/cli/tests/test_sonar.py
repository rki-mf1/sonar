import pytest
from sonar_cli import sonar


def test_no_args():
    """ """
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        sonar.main(None)

    assert pytest_wrapped_e.type == SystemExit


def test_parse_subject_first_info():
    args = sonar.parse_args(["info", "show", "--db", "http://cli.example/api"])
    assert args.resource == "info"
    assert args.verb == "show"


def test_parse_subject_first_match():
    args = sonar.parse_args(["sample", "match", "-r", "MN908947.3"])
    assert args.resource == "sample"
    assert args.verb == "match"


def test_flat_command_is_rejected():
    with pytest.raises(SystemExit):
        sonar.parse_args(["list-ref"])
