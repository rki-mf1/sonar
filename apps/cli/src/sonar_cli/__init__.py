import os
import tomllib

file_path = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(file_path))

with open(os.path.join(ROOT_DIR, "pyproject.toml"), "rb") as f:
    _META = tomllib.load(f)

NAME = _META["tool"]["poetry"]["name"]
VERSION = _META["tool"]["poetry"]["version"]
DESCRIPTION = _META["tool"]["poetry"]["description"]
