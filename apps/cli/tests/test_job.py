from tests.conftest import run_cli


def test_get_list_job(capfd, api_url):
    code = run_cli(f" tasks --db {api_url} --list-jobs")
    out, err = capfd.readouterr()
    assert "Completed" in out
    assert code == 0


def test_get_job_id(capfd, api_url):
    code = run_cli(f" tasks --db {api_url} --jobid 'cli_failed-job'")
    out, err = capfd.readouterr()
    assert "Status: Failed" in out
    assert code == 0
