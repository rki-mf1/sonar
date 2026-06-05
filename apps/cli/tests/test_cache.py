import pickle

import pytest
from sonar_cli.cache import sonarCache


def test_paranoid_worker_is_picklable_for_forkserver():
    """
    The paranoid WorkerPool runs with a fork-safe start method ("forkserver")
    because pyarrow is not fork-safe. forkserver/spawn pickle the worker
    function, so it must be a staticmethod (picklable by reference) rather than
    a bound method (which would drag the unpicklable cache instance along).
    """
    worker = sonarCache.process_paranoid_batch_worker
    # No bound instance: it's a plain function, not a bound method.
    assert getattr(worker, "__self__", None) is None
    # Pickling by reference must succeed (this is what forkserver/spawn do).
    assert pickle.loads(pickle.dumps(worker)) is worker


def test_find_snpeff_config_uses_anno_config_file(monkeypatch, tmp_path):
    config_file = tmp_path / "custom-snpEff.config"
    config_file.write_text("test\n")

    monkeypatch.setattr("sonar_cli.cache.ANNO_CONFIG_FILE", str(config_file))
    monkeypatch.setattr("sonar_cli.cache.ANNO_TOOL_PATH", "snpEff")
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    cache = sonarCache.__new__(sonarCache)

    assert cache.find_snpeff_config() == str(config_file)


def test_find_snpeff_config_uses_tool_path_layout(monkeypatch, tmp_path):
    env_dir = tmp_path / "env"
    bin_dir = env_dir / "bin"
    share_dir = env_dir / "share" / "snpeff-5.2"
    bin_dir.mkdir(parents=True)
    share_dir.mkdir(parents=True)

    tool_path = bin_dir / "snpEff"
    tool_path.write_text("")
    config_file = share_dir / "snpEff.config"
    config_file.write_text("test\n")

    monkeypatch.setattr("sonar_cli.cache.ANNO_CONFIG_FILE", None)
    monkeypatch.setattr("sonar_cli.cache.ANNO_TOOL_PATH", str(tool_path))
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    cache = sonarCache.__new__(sonarCache)

    assert cache.find_snpeff_config() == str(config_file)


def test_find_snpeff_config_fails_without_any_source(monkeypatch):
    monkeypatch.setattr("sonar_cli.cache.ANNO_CONFIG_FILE", None)
    monkeypatch.setattr("sonar_cli.cache.ANNO_TOOL_PATH", "snpEff")
    monkeypatch.setattr("sonar_cli.cache.shutil.which", lambda _tool: None)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    cache = sonarCache.__new__(sonarCache)

    with pytest.raises(SystemExit) as exc_info:
        cache.find_snpeff_config()

    assert exc_info.value.code == 1
