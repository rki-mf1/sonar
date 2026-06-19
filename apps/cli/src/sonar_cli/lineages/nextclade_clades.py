"""Shared builder for Nextclade-style clade-designation sources.

RSV (``rsv-lineages/lineage-designation-*``) and seasonal influenza
(``influenza-clade-nomenclature/*``) publish their lineage designations in an
identical, auto-generated tab-separated format with the columns::

    clade   gene    site    alt

Rows where ``gene == "clade"`` encode the parent of ``clade`` in the ``site``
column (e.g. ``A.2.1  clade  A.2``). A clade that never appears in such a row is
a root (no parent). All other rows are mutation definitions and are ignored
here.

The per-organism modules in this package only declare their source URLs and
delegate to :func:`build_lineage_file`, which converts the sources into the same
two-column ``lineage``/``sublineage`` TSV that the backend importer already
consumes (see ``sc2_lineages.py`` and ``import_lineage.py``).
"""

import pandas as pd
from sonar_cli.lineages.common import pairs_to_lineage_file

CLADE_COLUMNS = ["clade", "gene", "site", "alt"]


def read_clade_pairs(sources: list[str]) -> pd.DataFrame:
    """Read clade-definition sources into unique ``(lineage, parent)`` pairs.

    Args:
        sources: One or more paths/URLs to clade/gene/site/alt TSV files.

    Returns:
        DataFrame with columns ``lineage`` and ``parent`` ("none" for roots).
    """
    names: set[str] = set()
    parents: dict[str, str] = {}

    for source in sources:
        df = pd.read_csv(source, sep="\t", dtype=str).fillna("")
        for clade, gene, site, _alt in df[CLADE_COLUMNS].itertuples(index=False):
            clade = clade.strip()
            if not clade:
                continue
            names.add(clade)
            if gene.strip() == "clade":
                parent = site.strip()
                if parent:
                    # First occurrence wins, mirroring the backend importer.
                    parents.setdefault(clade, parent)
                    names.add(parent)

    rows = [(name, parents.get(name, "none")) for name in sorted(names)]
    return pd.DataFrame(rows, columns=["lineage", "parent"])


def build_lineage_file(sources: list[str], output_file: str) -> str:
    """Build the backend ``lineage``/``sublineage`` TSV from clade sources."""
    return pairs_to_lineage_file(read_clade_pairs(sources), output_file)
