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
        if file:
            self.lineage_file = file
            return
        # Can we remove this? playwright-e2e is failing without
        self.lineage_file = "lineage-test-data/lineages_test.tsv"

    def process_lineage_data(self):
        """
        Process the lineage data.
        """
        tsv_data = pd.read_csv(self.lineage_file, sep="\t")

        # Use a single dictionary to track all lineage objects
        all_lineages: dict[str, Lineage] = {}

        # First pass: Create all lineage objects
        for lineage, sublineages in tsv_data.itertuples(index=False):
            # Ensure the lineage is added even if it has no children
            if lineage not in all_lineages:
                all_lineages[lineage] = Lineage(name=lineage)

            # Process sublineages if they exist and create them if needed
            if sublineages != "none":
                if sublineages not in all_lineages:
                    all_lineages[sublineages] = Lineage(name=sublineages)

        # Second pass: Set parent relationships
        for lineage, sublineages in tsv_data.itertuples(index=False):
            if sublineages != "none":

                if all_lineages[sublineages].parent is None:
                    all_lineages[sublineages].parent = all_lineages[lineage]

        # Save all lineages to the database
        # Separate into parents (no parent set) and children (parent set)
        parents_to_save = [
            lineage_obj
            for lineage_obj in all_lineages.values()
            if lineage_obj.parent is None
        ]
        children_to_save = [
            lineage_obj
            for lineage_obj in all_lineages.values()
            if lineage_obj.parent is not None
        ]

        with transaction.atomic():
            # Save parents first so they have IDs
            for parent in parents_to_save:
                parent.save()
            # Then save children
            for child in children_to_save:
                child.save()

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
