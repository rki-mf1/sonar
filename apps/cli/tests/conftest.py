import re
import subprocess

import pytest
from sonar_cli import sonar
from sonar_cli.annotation import Annotator
from sonar_cli.cache import sonarCache
from sonar_cli.config import ANNO_TOOL_PATH


# Assuming Django API is running on localhost
API_BASE_URL = "http://127.0.0.1:8000/api"
ACCESION_SARSCOV2 = "MN908947.3"


@pytest.fixture(scope="session")
def api_url():
    return API_BASE_URL


@pytest.fixture(scope="session")
def accesion_SARSCOV2():
    return ACCESION_SARSCOV2


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


def run_cli_cmd(command):
    """
    A helper function to run the CLI command over cmd or subprocess.
    """
    return subprocess.run(command, shell=True)


@pytest.fixture(scope="session")
def annotator(accesion_SARSCOV2, tmpfile_name):
    sonar_cache = sonarCache(
        db=API_BASE_URL,
        outdir=tmpfile_name,
        logfile="import.log",
        allow_updates=False,
        temp=False,
        debug=False,
        disable_progress=False,
        refacc=accesion_SARSCOV2,
    )
    return Annotator(
        annotator_exe_path=ANNO_TOOL_PATH,
        cache=sonar_cache,
    )
