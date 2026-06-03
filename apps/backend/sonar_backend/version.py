import os
from pathlib import Path
import tomllib

UNKNOWN_VERSION = "0+unknown"


def _read_version_file() -> str | None:
    for parent in Path(__file__).resolve().parents:
        version_file = parent / "VERSION"
        if version_file.is_file():
            version = version_file.read_text(encoding="utf-8").strip()
            if version:
                return version
    return None


def _read_pyproject_version() -> str | None:
    for parent in Path(__file__).resolve().parents:
        pyproject = parent / "pyproject.toml"
        if pyproject.is_file():
            with pyproject.open("rb") as f:
                metadata = tomllib.load(f)
            return metadata["tool"]["poetry"]["version"]
    return None


def get_version() -> str:
    env_version = os.environ.get("SONAR_VERSION", "").strip()
    if env_version:
        return env_version
    return _read_version_file() or _read_pyproject_version() or UNKNOWN_VERSION
