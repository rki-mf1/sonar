"""Single source-of-truth for every supported pathogen's lineage definitions.

Each pathogen maps to a parser engine plus its source URL(s):
  - ``sc2``       : SARS-CoV-2 Pango generator (sc2_lineages, no source URL)
  - ``nextclade`` : Nextclade-style clade/gene/site/alt TSV(s) (RSV, influenza)
  - ``json``      : JSON name/parent designation (mpox)

To add a virus, add ONE row to ``PATHOGEN_SOURCES``. The builders and the CLI
``--pathogen`` choices are derived from it, so they never drift apart.
"""

from functools import partial

from sonar_cli.lineages import json_lineages
from sonar_cli.lineages import nextclade_clades
from sonar_cli.lineages.sc2_lineages import main as sc2_main

SC2 = "sc2"
NEXTCLADE = "nextclade"
JSON = "json"

_RSV = "https://raw.githubusercontent.com/rsv-lineages/lineage-designation-{}/main/.auto-generated/lineages.tsv"
_FLU = "https://raw.githubusercontent.com/influenza-clade-nomenclature/seasonal_{}_HA/main/.auto-generated/subclades.tsv"
_FLU_YAM = "https://raw.githubusercontent.com/nextstrain/seasonal-flu/master/config/nextstrain_clades_yam_ha.tsv"
_MPOX = "https://raw.githubusercontent.com/mpxv-lineages/lineage-designation/master/auto-generated/lineages.json"

# pathogen key -> (parser engine, [source URLs])
PATHOGEN_SOURCES = {
    "SARS-CoV-2": (SC2, []),
    "RSV-A": (NEXTCLADE, [_RSV.format("A")]),
    "RSV-B": (NEXTCLADE, [_RSV.format("B")]),
    "flu-H3N2": (NEXTCLADE, [_FLU.format("A-H3N2")]),
    "flu-H1N1pdm": (NEXTCLADE, [_FLU.format("A-H1N1pdm")]),
    "flu-Bvic": (NEXTCLADE, [_FLU.format("B-Vic")]),
    "flu-Byam": (NEXTCLADE, [_FLU_YAM]),
    "mpox": (JSON, [_MPOX]),
}


def _build(pathogen: str, output_file: str) -> str:
    """Generate the backend lineage TSV for ``pathogen`` at ``output_file``."""
    parser, sources = PATHOGEN_SOURCES[pathogen]
    if parser == SC2:
        return sc2_main(output_file=output_file)
    if parser == NEXTCLADE:
        return nextclade_clades.build_lineage_file(sources, output_file)
    if parser == JSON:
        return json_lineages.build_lineage_file(sources[0], output_file)
    raise ValueError(f"Unknown parser '{parser}' for pathogen '{pathogen}'")


PATHOGEN_BUILDERS = {key: partial(_build, key) for key in PATHOGEN_SOURCES}

# Exposed for argparse choices so the CLI and registry never drift apart.
PATHOGEN_CHOICES = list(PATHOGEN_BUILDERS)
