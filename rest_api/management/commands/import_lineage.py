import json
import os
import shutil
from tempfile import mkdtemp
from typing import List, Optional

import pandas as pd
import requests


from django.core.management.base import BaseCommand

from rest_api.models import Lineage, LineageAlias


class LineageImport:
    """
    sonarLinmgr class is used to manage the lineages.

    Attributes:
        _tmpdir (str): Temporary directory.
        _linurl (str): URL of the lineages file.
        _aliurl (str): URL of the alias file.
        lineage_file (str): Local path of the lineages file.
        alias_file (str): Local path of the alias file.
    """

    def __init__(self, tmpdir: Optional[str] = None):
        """
        sonarLinmgr Constructor.

        Args:
            tmpdir (str): Temporary directory.
        """
        self._tmpdir = mkdtemp(prefix=".tmp_sonarLinmgr_")
        self._linurl = "https://raw.githubusercontent.com/cov-lineages/pango-designation/master/lineages.csv"
        self._aliurl = "https://raw.githubusercontent.com/cov-lineages/pango-designation/master/pango_designation/alias_key.json"
        self.lineage_file = os.path.join(self._tmpdir, "lineages.csv")
        self.alias_file = os.path.join(self._tmpdir, "alias.json")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        shutil.rmtree(self._tmpdir)

    def download_lineage_data(self):
        """
        Download lineage and alias data.
        """
        # Download and write the lineage file
        print(f"Downloading lineage info from: {self._linurl}")
        try:
            url_content = requests.get(self._linurl)
            with open(self.lineage_file, "wb") as handle:
                handle.write(url_content.content)
        except:
            print("Connection refused by the server..")
            print("Using local data..")
            self.lineage_file = "test-data/lineages_2024_01_15.csv"

    def download_alias_data(self):
        """
        Download alias data.
        """
        # Download and write the alias file
        print(f"Downloading lineage aliases info from: {self._aliurl}")
        try:
            items = requests.get(self._aliurl)
            with open(self.alias_file, "w") as handle:
                json.dump(items.json(), handle)
        except:
            print("Connection refused by the server..")
            print("Using local data..")
            self.alias_file = "test-data/alias_key_2024_01_15.json"

    def process_lineage_data(self) -> List[Lineage]:
        """
        Process the lineage data.
        """
        with open(self.alias_file) as f:
            alias_json = json.load(f)
        aliases = []
        alias_lineages = []
        for key, value in alias_json.items():
            if isinstance(value, str):
                if "." in value:
                    lineage = self.get_or_create_lineage_obj(
                        value, alias_lineages, alias_json
                    )
                    alias_lineages.append(lineage)
                    aliases.append(LineageAlias(alias=key, lineage=lineage))
                else:
                    aliases.append(LineageAlias(alias=key, parent_alias=value))
            else:
                for item in value:
                    if "." in item:
                        lineage = self.get_or_create_lineage_obj(
                            item, alias_lineages, alias_json
                        )
                        alias_lineages.append(lineage)
                        aliases.append(LineageAlias(alias=key, lineage=lineage))
                    else:
                        aliases.append(LineageAlias(alias=key, parent_alias=item))

        [lineage.save() for lineage in alias_lineages]
        LineageAlias.objects.bulk_create(
            aliases,
            ignore_conflicts=True,
        )

        df_lineages = pd.read_csv(self.lineage_file, usecols=[0, 1])
        lineage_ids = df_lineages.lineage.unique()
        lineages = [
            self.get_or_create_lineage_obj(lineage_id, [], alias_json)
            for lineage_id in lineage_ids
        ]
        return lineages

    def get_or_create_lineage_obj(
        self, lineage: str, lineage_list: List[Lineage], alias_dict: dict
    ) -> Lineage:
        split = lineage.split(".")
        if split[0] in alias_dict.keys():
            alias = split.pop(0)
            return next(
                (
                    lineage
                    for lineage in lineage_list
                    if lineage.lineage == ".".join(split)
                    and lineage.prefixed_alias == alias
                ),
                None,
            ) or Lineage(lineage=".".join(split), prefixed_alias=alias)
        return Lineage(lineage=lineage)

    def update_lineage_data(self, alias_key: str, lineages: str) -> List[Lineage]:
        """
        Update the lineage data.

        Returns:
            pd.DataFrame: The dataframe with updated data.
        """
        if alias_key:
            self.alias_file = alias_key
        else:
            self.download_alias_data()

        if lineages:
            self.lineage_file = lineages
        else:
            self.download_lineage_data()

        df = self.process_lineage_data()
        return df


class Command(BaseCommand):
    help = (
        "Download latest pangolin information and import the information to a database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--alias-key",
            help="Pangolin alias_key.json file (default: auto download from GitHub)",
            type=str,
            default=None,
        )
        parser.add_argument(
            "--lineages",
            help="Pangolin lineages.csv file (default: auto download from GitHub)",
            type=str,
            default=None,
        )

    def handle(self, *args, **kwargs):
        Lineage.objects.all().delete()
        LineageAlias.objects.all().delete()
        with LineageImport() as lineage_manager:
            lineages = lineage_manager.update_lineage_data(
                kwargs["alias_key"], kwargs["lineages"]
            )
        Lineage.objects.bulk_create(
            objs=lineages,
            ignore_conflicts=True,
        )
        print("--Done--")
