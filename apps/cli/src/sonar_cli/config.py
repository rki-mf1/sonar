import os
from pathlib import Path
from tempfile import mkdtemp

from dotenv import dotenv_values

DEFAULTS = {
    "API_URL": "http://127.0.0.1:9080/api",
    "SECRET_KEY": "development-secret",
    "LOG_LEVEL": "INFO",
    "CHUNK_SIZE": "10000",
    "ANNO_CHUNK_SIZE": "250",
    "PROP_CHUNK_SIZE": "1000",
    "PARANOID_CHUNK_SIZE": "50",
    "PARANOID_N_JOBS": "8",
    "CACHE_CLEAR_CHUNK_SIZE": "250",
    "CACHE_CLEAR_N_JOBS": "4",
    "FILTER_DELETE_SIZE": "2000",
    "MATCH_CHUNK_LIMIT": "300",
    "ANNO_TOOL_PATH": "snpEff",
    "ANNO_CONFIG_FILE": "",
    "KSIZE": "11",
    "SCALED": "1",
}


def _get_xdg_config_path() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "sonar-cli" / "sonar-cli.config"
    return Path.home() / ".config" / "sonar-cli" / "sonar-cli.config"


def _load_file_config() -> dict[str, str]:
    config_path = _get_xdg_config_path()
    if not config_path.exists():
        return {}
    return {
        key: value
        for key, value in dotenv_values(config_path).items()
        if value is not None and value != ""
    }


_FILE_CONFIG = _load_file_config()
_RUNTIME_OVERRIDES: dict[str, str] = {}


def get_setting(name: str, default=None):
    runtime_value = _RUNTIME_OVERRIDES.get(name)
    if runtime_value not in (None, ""):
        return runtime_value

    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return env_value

    file_value = _FILE_CONFIG.get(name)
    if file_value not in (None, ""):
        return file_value

    return default


def set_runtime_override(name: str, value: str | None) -> None:
    if value in (None, ""):
        _RUNTIME_OVERRIDES.pop(name, None)
    else:
        _RUNTIME_OVERRIDES[name] = value


def resolve_base_url(override: str | None = None) -> str:
    if override not in (None, ""):
        return override
    return get_setting("API_URL", DEFAULTS["API_URL"])


def get_base_url() -> str:
    return resolve_base_url()


# (access token?)
SECRET_KEY = get_setting("SECRET_KEY", DEFAULTS["SECRET_KEY"])

DEBUG = False

# 10 = DEBUG, 20 = INFO, 30 = WARNING
LOG_LEVEL = get_setting("LOG_LEVEL", DEFAULTS["LOG_LEVEL"])

CHUNK_SIZE = int(get_setting("CHUNK_SIZE", DEFAULTS["CHUNK_SIZE"]))
ANNO_CHUNK_SIZE = int(get_setting("ANNO_CHUNK_SIZE", DEFAULTS["ANNO_CHUNK_SIZE"]))
PROP_CHUNK_SIZE = int(get_setting("PROP_CHUNK_SIZE", DEFAULTS["PROP_CHUNK_SIZE"]))

# Parallel processing defaults
PARANOID_CHUNK_SIZE = int(
    get_setting("PARANOID_CHUNK_SIZE", DEFAULTS["PARANOID_CHUNK_SIZE"])
)
PARANOID_N_JOBS = int(get_setting("PARANOID_N_JOBS", DEFAULTS["PARANOID_N_JOBS"]))
CACHE_CLEAR_CHUNK_SIZE = int(
    get_setting("CACHE_CLEAR_CHUNK_SIZE", DEFAULTS["CACHE_CLEAR_CHUNK_SIZE"])
)
CACHE_CLEAR_N_JOBS = int(
    get_setting("CACHE_CLEAR_N_JOBS", DEFAULTS["CACHE_CLEAR_N_JOBS"])
)

FILTER_DELETE_SIZE = int(
    get_setting("FILTER_DELETE_SIZE", DEFAULTS["FILTER_DELETE_SIZE"])
)

# Page size for the match command pagination loop.
# The CLI fetches results in chunks of this size instead of requesting
# everything at once, to avoid high memory usage and backend timeouts.
MATCH_CHUNK_LIMIT = int(get_setting("MATCH_CHUNK_LIMIT", DEFAULTS["MATCH_CHUNK_LIMIT"]))

TMP_CACHE = os.path.abspath(mkdtemp(prefix=".sonarCache_"))

ANNO_TOOL_PATH = get_setting("ANNO_TOOL_PATH", DEFAULTS["ANNO_TOOL_PATH"])
ANNO_CONFIG_FILE = get_setting("ANNO_CONFIG_FILE", DEFAULTS["ANNO_CONFIG_FILE"]) or None
# SNPSIFT_TOOL_PATH = os.getenv("SNPSIFT_TOOL_PATH","")
# VCF_ONEPERLINE_PATH = os.getenv("VCF_ONEPERLINE_PATH","")

MAX_SUPPORTED_DB_VERSION = 2
SUPPORTED_DB_VERSION = 1.2

# API/Backend
BASE_URL = get_base_url()

# For sourmash
KSIZE = int(get_setting("KSIZE", DEFAULTS["KSIZE"]))
SCALED = int(get_setting("SCALED", DEFAULTS["SCALED"]))
