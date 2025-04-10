import pandas as pd
from pango_aliasor.aliasor import Aliasor


def main(output_file):
    path_lineages = "https://raw.githubusercontent.com/cov-lineages/pango-designation/master/lineage_notes.txt"
    all_lineages = [
        lineage
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
    df = pd.merge(df, df, left_on="lineage", right_on="parent", how="left")
    df = (
        df[["lineage_x", "lineage_y"]]
        .rename(columns={"lineage_x": "lineage", "lineage_y": "sublineage"})
        .dropna(subset=["sublineage"])
    )

    df.to_csv(output_file, sep="\t", index=False)

    return output_file
