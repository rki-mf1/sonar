import re

import pytest
from sonar_cli import sonar


# Assuming Django API is running on localhost
API_BASE_URL = "http://127.0.0.1:8000/api"


# PYTEST FIXTURES
# @pytest.fixture(autouse=True)
# def mock_workerpool_imap_unordered(monkeypatch):
#     """Mock mpire's WorkerPool.imap_unordered function
#     This is necessary to work around crashes caused by trying to calculate
#     coverage with multiprocess subprocesses, and also to make the tests
#     reproducible (ordered).
#     """
#     monkeypatch.setattr(
#         "mpire.WorkerPool.imap_unordered",
#         lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
#             func(**arg) for arg in args
#         ),
#     )

# monkeypatch.setattr("mpire.WorkerPool")


@pytest.fixture(scope="session")
def api_url():
    return API_BASE_URL


@pytest.fixture(scope="session")
def tmpfile_name(tmpdir_factory):
    my_tmpdir = str(tmpdir_factory.mktemp("sonar-cli_test"))
    # .join(
    #        next(tempfile._get_candidate_names())
    #    )
    print("tmp_path:", my_tmpdir)
    yield my_tmpdir


def split_cli(s):
    """Split a string into a list of individual arguments, respecting quotes"""
    return re.findall(r'(?:[^\s,"\']|"(?:\\.|[^"])*")+', s)
    # re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*")+', s)


def run_cli(s):
    """Helper function to simulate running the command line ./sonar <args>"""
    return sonar.main(sonar.parse_args(split_cli(s)))
