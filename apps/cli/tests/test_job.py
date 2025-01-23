from tests.conftest import run_cli


def test_get_list_job(capfd, api_url):
    code = run_cli(f" tasks --db {api_url} --list-jobs")
    out, err = capfd.readouterr()
    # assert "Failed" in out
    assert "Completed" in out
    assert code == 0


def test_get_job_id(capfd, api_url):
    # code = run_cli(f" tasks --db {api_url} --jobid 'cli_queue-job'")
    code = run_cli(
        f" tasks --db {api_url} --jobid 'cli_prop_a6281e0b-f5c0-458e-9783-5f992a0fa03a'"
    )
    out, err = capfd.readouterr()
    # assert "Status: Queued" in out
    assert "Status: Completed" in out
    assert code == 0
