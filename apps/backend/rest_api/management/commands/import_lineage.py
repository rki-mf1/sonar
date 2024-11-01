import os
import shutil
from tempfile import mkdtemp
from typing import List
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction
import pandas as pd
from rest_api.models import Lineage


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
        self.lineage_file = os.path.join(self._tmpdir, "lineages.csv")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        shutil.rmtree(self._tmpdir)

    def set_file(self, file: str | None = None) -> None:
        """
        Download lineage and alias data.
        """
        if file:
            self.lineage_file = file
            return
        self.lineage_file = "test-data/lineages_test.tsv"

    def process_lineage_data(self):
        """
        Process the lineage data.
        """
        with open(self.lineage_file) as f:
            tsv_data = pd.read_csv(self.lineage_file, sep="\t")
        parents: dict[str, Lineage] = {}
        children: list[Lineage] = []
        for lineage, sublineages in tsv_data.itertuples(index=False):
            if sublineages == "none":
                continue
            values = sublineages.split(",")
            if lineage not in parents:
                parents[lineage] = Lineage(name=lineage)
            for val in values:
                children.append(Lineage(name=val, parent=parents[lineage]))
        with transaction.atomic():
            for parent in parents.values():
                parent.save()
            Lineage.objects.bulk_create(
                objs=children,
                ignore_conflicts=True,
            )

    def update_lineage_data(self, lineages: str) -> List[Lineage]:
        """
        Update the lineage data.

        Returns:
            pd.DataFrame: The dataframe with updated data.
        """
        if lineages:
            self.lineage_file = lineages
        else:
            self.set_file()

        df = self.process_lineage_data()
        return df


class Command(BaseCommand):
    help = "import lineage tsv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--lineages",
            help="lineages.tsv file",
            type=str,
            default=None,
        )

    def handle(self, *args, **kwargs):
        Lineage.objects.all().delete()
        with LineageImport() as lineage_manager:
            lineages = lineage_manager.update_lineage_data(kwargs["lineages"])
        print("--Done--")
