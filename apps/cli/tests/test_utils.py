from unittest.mock import MagicMock

from sonar_cli.utils1 import sonarUtils1

LOGGER = MagicMock()


def test_get_job_byID(monkeypatch, api_url):
    job_id = "cli_failed-job"
    expected_status = "Failed"
    monkeypatch.setattr("sonar_cli.utils1", sonarUtils1)

    modified_data, status = sonarUtils1.get_job_byID(api_url, job_id)

    assert status == expected_status


# @patch("time.sleep", return_value=None)
# def test_get_job_byID_background_interrupted(monkeypatch):
#     db = None
#     job_id = "cli_fail-job"
#     interval = 1

#     with pytest.raises(SystemExit):


#         sonarUtils1.get_job_byID(db, job_id, background=True, interval=interval
#         )

#         MagicMock('sonarUtils1.get_job_byID', side_effect=KeyboardInterrupt)

#     LOGGER.warning.assert_called_once_with("Process interrupted by user. Exiting...")
