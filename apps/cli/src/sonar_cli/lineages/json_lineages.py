"""Builder for JSON lineage-designation sources.

mpox (``mpxv-lineages/lineage-designation``) publishes its designations as a
JSON document with a ``lineages`` array of objects that carry an explicit
``name`` and ``parent`` (e.g. ``{"name": "A.1.1", "parent": "A.1", ...}``). This
maps directly onto our parent-child model.
"""

import json
from urllib.request import urlopen

import pandas as pd
from sonar_cli.lineages.common import pairs_to_lineage_file

# Sentinels that mean "no parent" (mpox uses the literal string "None" for roots).
_NULL_PARENTS = {"", "none", "null", "na"}


def _load_json(source: str):
    if str(source).startswith(("http://", "https://")):
        with urlopen(source) as response:  # nosec B310 - fixed https sources
            return json.load(response)
    with open(source) as fh:
        return json.load(fh)


def read_json_pairs(source: str) -> pd.DataFrame:
    """Read a JSON designation into unique ``(lineage, parent)`` pairs.

    Accepts either a top-level list of entries or an object with a ``lineages``
    array. Each entry needs a ``name``; ``parent`` is optional (missing/null =
    root). Any referenced parent is also materialised as a node, so a parent
    that is not itself an entry becomes a root rather than dropping its children.
    """
    data = _load_json(source)
    entries = data["lineages"] if isinstance(data, dict) else data

    names: set[str] = set()
    parents: dict[str, str] = {}
    for entry in entries:
        name = str(entry["name"]).strip()
        if not name:
            continue
        names.add(name)
        parent = entry.get("parent")
        if parent is not None:
            parent = str(parent).strip()
            if parent.lower() not in _NULL_PARENTS:
                parents.setdefault(name, parent)
                names.add(parent)

    rows = [(name, parents.get(name, "none")) for name in sorted(names)]
    return pd.DataFrame(rows, columns=["lineage", "parent"])


def build_lineage_file(source: str, output_file: str) -> str:
    """Build the backend ``lineage``/``sublineage`` TSV from a JSON source."""
    return pairs_to_lineage_file(read_json_pairs(source), output_file)
