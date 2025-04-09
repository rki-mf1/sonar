import pytest

from sonar_cli import sonar


@pytest.mark.clionly
def test_no_args():
    """ """
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        sonar.main(None)

    assert pytest_wrapped_e.type is SystemExit
