import tempfile

import pytest


# Assuming Django API is running on localhost
API_BASE_URL = "http://127.0.0.1:8000/"


@pytest.fixture(scope="session")
def api_url():
    return API_BASE_URL


@pytest.fixture
def tmpfile_name(tmpdir_factory):
    my_tmpdir = str(
        tmpdir_factory.mktemp("dbm_test").join(next(tempfile._get_candidate_names()))
    )
    print("tmp_path:", my_tmpdir)

    yield my_tmpdir
