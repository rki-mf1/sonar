from importlib import metadata
import os
from pathlib import Path
import tomllib

PACKAGE_DIR = Path(__file__).resolve().parents[2]
UNKNOWN_VERSION = "0+unknown"


def _read_package_metadata() -> dict[str, str]:
    pyproject = PACKAGE_DIR / "pyproject.toml"
    if pyproject.is_file():
        with pyproject.open("rb") as f:
            project_metadata = tomllib.load(f)["tool"]["poetry"]
        return {
            "name": project_metadata["name"],
            "version": project_metadata["version"],
            "description": project_metadata["description"],
        }

    try:
        package_metadata = metadata.metadata("sonar-cli")
        return {
            "name": package_metadata["Name"],
            "version": metadata.version("sonar-cli"),
            "description": package_metadata.get("Summary", ""),
        }
    except metadata.PackageNotFoundError:
        return {"name": "sonar-cli", "version": UNKNOWN_VERSION, "description": ""}


def _read_version_file() -> str | None:
    for parent in Path(__file__).resolve().parents:
        version_file = parent / "VERSION"
        if version_file.is_file():
            version = version_file.read_text(encoding="utf-8").strip()
            if version:
                return version
    return None


def get_version() -> str:
    env_version = os.environ.get("SONAR_VERSION", "").strip()
    if env_version:
        return env_version
    return _read_version_file() or _META["version"]


_META = _read_package_metadata()

NAME = _META["name"]
VERSION = get_version()
DESCRIPTION = _META["description"]
