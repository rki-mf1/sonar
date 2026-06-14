"""Shared transform for lineage builders.

Every source parser reduces its input to a table of ``(lineage, parent)`` pairs
("none" for roots); this module turns that into the two-column
``lineage``/``sublineage`` TSV the backend importer consumes. Keeping the
transform here lets the per-format parsers (Nextclade clade TSV, JSON
designations, ...) stay tiny and identical in output.
"""

import pandas as pd


def pairs_to_lineage_file(pairs: pd.DataFrame, output_file: str) -> str:
    """Convert ``(lineage, parent)`` pairs into the backend lineage TSV.

    Args:
        pairs: DataFrame with columns ``lineage`` and ``parent`` ("none" roots).
        output_file: destination path.

    The output mirrors ``sc2_lineages.main``: one row per direct parent->child
    relationship, plus a ``none`` row for any isolated lineage that has neither a
    parent nor children.
    """
    # Self-join to list each lineage's DIRECT sublineages (one per row).
    df_mapping = (
        pd.merge(pairs, pairs, left_on="lineage", right_on="parent", how="left")[
            ["lineage_x", "lineage_y"]
        ]
        .rename(columns={"lineage_x": "lineage", "lineage_y": "sublineage"})
        .dropna(subset=["sublineage"])
    )

    # Lineages with neither parent nor children need an explicit "none" row.
    orphan_lineages = pairs[
        (pairs["parent"] == "none") & (~pairs["lineage"].isin(df_mapping["lineage"]))
    ].assign(sublineage="none")[["lineage", "sublineage"]]

    final_df = pd.concat([df_mapping, orphan_lineages], ignore_index=True)
    final_df.to_csv(output_file, sep="\t", index=False)

    return output_file
