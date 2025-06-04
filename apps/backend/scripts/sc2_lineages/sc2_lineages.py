#!/usr/bin/env python
## run command: python sc2_lineages.py -o sc2_lineages.tsv

import argparse

import pandas as pd
from pango_aliasor.aliasor import Aliasor


def main():

    parser = argparse.ArgumentParser(
        description="Create file with all pangolin lineages mapped to their direct sublineages."
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Path and name of output tsv file."
    )

    args = parser.parse_args()
    output_file = args.output

    path_lineages = "https://raw.githubusercontent.com/cov-lineages/pango-designation/master/lineage_notes.txt"
    all_lineages = [
        lineage.split(" ")[
            0
        ]  # for poorly formatted lineages (like in the case of "PN.1 ...")
        for lineage in pd.read_csv(path_lineages, sep="\t").iloc[:, 0].tolist()
        if not lineage.startswith("*")
    ]

    # If no alias_key.json is passed, downloads the latest version from github # Aliasor('alias_key.json')
    aliasor = Aliasor()
    df = pd.DataFrame(
        {
            "lineage": all_lineages,
            "parent": [
                "none" if aliasor.parent(lineage) == "" else aliasor.parent(lineage)
                for lineage in all_lineages
            ],  # e.g: aliasor.parent("BQ.1") # 'BE.1.1.1'
        }
    )

    # Perform a self-join to get all DIRECT sublineages for each lineage (one per row)
    # Join each 'lineage' with matching 'parent' to get each direct sublineage
    df_mapping = (
        pd.merge(df, df, left_on="lineage", right_on="parent", how="left")[
            ["lineage_x", "lineage_y"]
        ]
        .rename(columns={"lineage_x": "lineage", "lineage_y": "sublineage"})
        .dropna(subset=["sublineage"])
    )

    # lineages without parents and without children wont be considered in the mapping and need to be appended separately
    orphan_lineages = df[
        (df["parent"] == "none") & (~df["lineage"].isin(df_mapping["lineage"]))
    ].assign(sublineage="none")[["lineage", "sublineage"]]

    final_df = pd.concat(
        [df_mapping.dropna(subset=["sublineage"]), orphan_lineages], ignore_index=True
    )
    final_df.to_csv(output_file, sep="\t", index=False)

    return 0


if __name__ == "__main__":
    main()
