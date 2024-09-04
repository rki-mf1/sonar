import json
import os
import shutil
from tempfile import mkdtemp
from typing import List, Optional

import pandas as pd
import requests


from django.core.management.base import BaseCommand
from django.db import transaction

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

    def import_lineage_data(self):
        """
        Download lineage and alias data.
        """
        self.lineage_file = "test-data/lineages_test.tsv"
            
    def process_lineage_data(self) -> list[Lineage]:
        """
        Process the lineage data.
        """
        with open(self.lineage_file) as f:
            tsv_data = pd.read_csv(self.lineage_file, sep="\t")
        
        parents: list[Lineage] = []
        children: list[Lineage] = []
        # all_sublineages = set()
        # all_parents = set()
        for lineage, sublineages in tsv_data.itertuples(index=False):
            if sublineages == "none":
                continue
            values = sublineages.split(",")
           # all_sublineages.update(values)   
           # all_parents.add(lineage)
            parent = Lineage(name=lineage)
            parents.append(parent)
            for val in values:                
                children.append(Lineage(name=val, parent=parent))  
       
        # in parents only names of "root" lineages without parent:
        # roots = all_parents-all_sublineages    
        with transaction.atomic():  
            for parent in parents:
                parent.save()          
            # Lineage.objects.bulk_create(
                # objs=parents,
                # ignore_conflicts=True,
            # )
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
            self.import_lineage_data()

        df = self.process_lineage_data()
        return df


class Command(BaseCommand):
    help = (
        "import lineage tsv"
    )

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
            lineages = lineage_manager.update_lineage_data(
                kwargs["lineages"]
            )        
        print("--Done--")
