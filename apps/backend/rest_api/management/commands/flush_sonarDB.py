from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Flush data in Sonar database only"

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                BEGIN;
                TRUNCATE "sample", "sample2property", "mutation2annotation", "reference", "property", "alignment",
                "gene_segment", "sequence", "annotation_type", "mutation", "gene", "lineage", "replicon",
                "alignment2mutation","processing_job","import_log","file_processing"
                RESTART IDENTITY;
                COMMIT;
            """
            )

        self.stdout.write(
            self.style.SUCCESS("Successfully truncated tables in Sonar database")
        )
