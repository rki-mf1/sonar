import importlib

from sonar_cli import config as config_module
from sonar_cli import sonar
from sonar_cli.utils1 import sonarUtils1


def reload_config(monkeypatch, tmp_path, *, api_url_env="", file_api_url=None):
    xdg_home = tmp_path / "xdg"
    config_dir = xdg_home / "sonar-cli"
    config_dir.mkdir(parents=True)

    config_file = config_dir / "sonar-cli.config"
    if file_api_url is not None:
        config_file.write_text(f"API_URL={file_api_url}\n")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))
    monkeypatch.setenv("API_URL", api_url_env)

    reloaded = importlib.reload(config_module)
    reloaded.set_runtime_override("API_URL", None)
    return reloaded


def test_api_url_uses_xdg_config(monkeypatch, tmp_path):
    config = reload_config(
        monkeypatch,
        tmp_path,
        api_url_env="",
        file_api_url="http://xdg-config.example/api",
    )

    assert config.get_base_url() == "http://xdg-config.example/api"


def test_api_url_env_overrides_xdg_config(monkeypatch, tmp_path):
    config = reload_config(
        monkeypatch,
        tmp_path,
        api_url_env="http://env.example/api",
        file_api_url="http://xdg-config.example/api",
    )

    assert config.get_base_url() == "http://env.example/api"


def test_runtime_override_overrides_env(monkeypatch, tmp_path):
    config = reload_config(
        monkeypatch,
        tmp_path,
        api_url_env="http://env.example/api",
        file_api_url="http://xdg-config.example/api",
    )

    config.set_runtime_override("API_URL", "http://override.example/api")

    assert config.get_base_url() == "http://override.example/api"


def test_sonar_main_sets_db_override(monkeypatch, tmp_path):
    config = reload_config(
        monkeypatch,
        tmp_path,
        api_url_env="http://env.example/api",
        file_api_url="http://xdg-config.example/api",
    )
    captured = {}

    monkeypatch.setattr(
        sonar,
        "execute_commands",
        lambda args: captured.setdefault("url", config.get_base_url()),
    )

    sonar.main(sonar.parse_args(["info", "--db", "http://cli.example/api"]))

    assert captured["url"] == "http://cli.example/api"


def test_utils1_uses_runtime_resolved_base_url(monkeypatch, tmp_path):
    config = reload_config(
        monkeypatch,
        tmp_path,
        api_url_env="http://env.example/api",
        file_api_url="http://xdg-config.example/api",
    )
    captured = {}

    class DummyClient:
        def __init__(self, base_url):
            captured["url"] = base_url

        def get_database_info(self):
            return {"detail": {}}

    monkeypatch.setattr("sonar_cli.utils1.APIClient", DummyClient)

    sonarUtils1.get_info()
    assert captured["url"] == "http://env.example/api"

    config.set_runtime_override("API_URL", "http://override.example/api")
    sonarUtils1.get_info()
    assert captured["url"] == "http://override.example/api"
