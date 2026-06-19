"""Unit tests for the multi-pathogen lineage builders.

These tests are network-free: they feed small Nextclade-style clade-definition
files (the exact format published by the RSV and influenza designation repos)
to the shared parser and check the resulting parent/child hierarchy.
"""

import json

import pandas as pd
from sonar_cli.lineages import json_lineages
from sonar_cli.lineages.nextclade_clades import build_lineage_file
from sonar_cli.lineages.nextclade_clades import read_clade_pairs
from sonar_cli.lineages.registry import PATHOGEN_BUILDERS
from sonar_cli.lineages.registry import PATHOGEN_CHOICES
from sonar_cli.lineages.registry import PATHOGEN_SOURCES


# A minimal RSV-style file. Rows with gene == "clade" encode the parent in the
# `site` column; everything else is a mutation definition and must be ignored.
RSV_LIKE = """clade\tgene\tsite\talt
A\tF\t16\tA
A\tN\t84\tR
A.1\tclade\tA\t
A.1\tF\t122\tA
A.2\tclade\tA\t
A.2.1\tclade\tA.2\t
A.2.1\tF\t125\tN
B\tF\t103\tA
B.1\tclade\tB\t
"""

# Influenza is split across two files (clades + subclades), same format.
FLU_CLADES = """clade\tgene\tsite\talt
A\tHA1\t45\tN
B\tHA1\t3\tI
"""
FLU_SUBCLADES = """clade\tgene\tsite\talt
A.2\tclade\tA\t
A.2\tHA2\t160\tN
B.1\tclade\tB\t
"""


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def _child_to_parent(output_file):
    """Reconstruct a child -> parent map from a built lineage/sublineage TSV."""
    df = pd.read_csv(output_file, sep="\t")
    mapping = {}
    for lineage, sublineage in df.itertuples(index=False):
        if sublineage != "none":
            mapping[sublineage] = lineage
    return mapping


def test_read_clade_pairs_extracts_parents(tmp_path):
    src = _write(tmp_path, "rsv.tsv", RSV_LIKE)
    df = read_clade_pairs([src])
    pairs = dict(df.itertuples(index=False))

    # Roots have no parent.
    assert pairs["A"] == "none"
    assert pairs["B"] == "none"
    # Children point at their parent from the gene == "clade" rows.
    assert pairs["A.1"] == "A"
    assert pairs["A.2"] == "A"
    assert pairs["A.2.1"] == "A.2"
    assert pairs["B.1"] == "B"
    # Mutation-only rows never invent extra lineages.
    assert set(pairs) == {"A", "A.1", "A.2", "A.2.1", "B", "B.1"}


def test_build_lineage_file_hierarchy(tmp_path):
    src = _write(tmp_path, "rsv.tsv", RSV_LIKE)
    out = build_lineage_file([src], str(tmp_path / "out.tsv"))
    mapping = _child_to_parent(out)

    assert mapping == {"A.1": "A", "A.2": "A", "A.2.1": "A.2", "B.1": "B"}
    # Roots must never appear as someone's sublineage.
    assert "A" not in mapping
    assert "B" not in mapping


def test_build_lineage_file_merges_multiple_sources(tmp_path):
    clades = _write(tmp_path, "clades.tsv", FLU_CLADES)
    subclades = _write(tmp_path, "subclades.tsv", FLU_SUBCLADES)
    out = build_lineage_file([clades, subclades], str(tmp_path / "out.tsv"))
    mapping = _child_to_parent(out)

    assert mapping == {"A.2": "A", "B.1": "B"}


def test_output_columns_match_backend_contract(tmp_path):
    src = _write(tmp_path, "rsv.tsv", RSV_LIKE)
    out = build_lineage_file([src], str(tmp_path / "out.tsv"))
    df = pd.read_csv(out, sep="\t")
    # The backend importer reads exactly these two columns by position.
    assert list(df.columns) == ["lineage", "sublineage"]


def test_isolated_lineage_gets_none_row(tmp_path):
    # A single root with no children must still be emitted with "none".
    src = _write(tmp_path, "solo.tsv", "clade\tgene\tsite\talt\nA\tF\t1\tG\n")
    out = build_lineage_file([src], str(tmp_path / "out.tsv"))
    df = pd.read_csv(out, sep="\t")
    assert df.to_dict("records") == [{"lineage": "A", "sublineage": "none"}]


# mpox publishes JSON entries with explicit name/parent; roots use the literal
# string "None" or JSON null, and a parent may be referenced before/without its
# own entry.
MPOX_LIKE = [
    {"name": "A", "parent": "None"},  # string sentinel -> root
    {"name": "A.1", "parent": "A"},
    {"name": "A.1.1", "parent": "A.1"},
    {"name": "B.1", "parent": "A.1.1"},
    {"name": "A.2", "parent": "A"},
]


def _write_json(tmp_path, name, obj):
    path = tmp_path / name
    path.write_text(json.dumps(obj))
    return str(path)


def test_json_pairs_handles_null_sentinels(tmp_path):
    # Root may be expressed as the string "None" or JSON null; neither should
    # create a lineage literally named "None".
    src = _write_json(
        tmp_path,
        "mpox.json",
        [{"name": "A", "parent": "None"}, {"name": "C", "parent": None}],
    )
    pairs = dict(json_lineages.read_json_pairs(src).itertuples(index=False))
    assert pairs == {"A": "none", "C": "none"}
    assert "None" not in pairs


def test_json_pairs_materialises_missing_parent(tmp_path):
    # A parent that is not itself an entry still becomes a (root) node so its
    # child is never dropped.
    src = _write_json(tmp_path, "x.json", [{"name": "X", "parent": "Y"}])
    pairs = dict(json_lineages.read_json_pairs(src).itertuples(index=False))
    assert pairs == {"X": "Y", "Y": "none"}


def test_json_build_hierarchy_and_dict_wrapper(tmp_path):
    # Accept both a bare list and a {"lineages": [...]} document.
    src = _write_json(tmp_path, "mpox.json", {"lineages": MPOX_LIKE})
    out = json_lineages.build_lineage_file(src, str(tmp_path / "out.tsv"))
    df = pd.read_csv(out, sep="\t")
    mapping = {s: l for l, s in df.itertuples(index=False) if s != "none"}
    assert mapping == {"A.1": "A", "A.1.1": "A.1", "B.1": "A.1.1", "A.2": "A"}
    assert "A" not in mapping  # the sole root
    assert list(df.columns) == ["lineage", "sublineage"]


def test_registry_choices_in_sync():
    assert PATHOGEN_CHOICES == list(PATHOGEN_BUILDERS)
    assert list(PATHOGEN_SOURCES) == PATHOGEN_CHOICES
    for key in (
        "SARS-CoV-2",
        "RSV-A",
        "RSV-B",
        "flu-H3N2",
        "flu-H1N1pdm",
        "flu-Bvic",
        "flu-Byam",
        "mpox",
    ):
        assert callable(PATHOGEN_BUILDERS[key])


def test_registry_sources_are_valid_urls():
    # Every non-SARS-CoV-2 pathogen declares at least one https source URL.
    for key, (parser, sources) in PATHOGEN_SOURCES.items():
        if key == "SARS-CoV-2":
            continue
        assert sources, f"{key} must declare at least one source URL"
        assert all(url.startswith("https://") for url in sources)
