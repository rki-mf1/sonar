from django.apps import apps
from django.db import connection
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import models
from .viewsets_sample import SampleFilterMixin
from .viewsets_statistics_and_plots import SampleViewSetPlots
from .viewsets_statistics_and_plots import SampleViewSetStatistics


class DatabaseInfoView(
    viewsets.GenericViewSet,
    SampleFilterMixin,
):
    @action(detail=False, methods=["get"])
    def get_database_tables_status(self, request, *args, **kwargs):
        """
        Checks if all required database tables are created and connected with Django.
        Returns True if all are ready, otherwise False.
        """
        # List of all tables from model
        # this also include django tables (e.g., auth_user)
        expected_tables = {model._meta.db_table for model in apps.get_models()}

        # sonar_db = [
        #     "sequence", "alignment",
        #     "alignment2mutation", "annotation_type",
        #     "replicon", "gene",
        #     "gene_segment", "lineage",
        #     "reference", "property",
        #     "sample", "sample2property",
        #     "mutation", "mutation2annotation",
        #     "processing_job", "file_processing",
        #     "import_log",
        # ]

        # Retrieve all actual tables from the database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
            )
            actual_tables = {row[0] for row in cursor.fetchall()}

        # Check for missing tables
        missing_tables = set(expected_tables) - actual_tables

        if missing_tables:
            return Response(
                data={"status": False, "missing_tables": list(missing_tables)},
                status=status.HTTP_200_OK,
            )

        return Response(data={"status": True}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])  # detail=False means it's a list action
    def get_database_info(self, request, *args, **kwargs):
        result = {}
        queryset = self.get_filtered_queryset(request)
        statistics = SampleViewSetStatistics().get_statistics()
        total_samples = statistics["samples_total"]
        metadata_coverage = SampleViewSetPlots().get_metadata_coverage(queryset)
        # Add percentages
        for key, count in metadata_coverage.items():
            percentage = (count / total_samples) * 100 if total_samples > 0 else 0
            metadata_coverage[key] = f"{count} ({percentage:.2f}%)"

        result["metadata_coverage"] = metadata_coverage
        result.update(
            {
                "samples_total": total_samples,
                "earliest_sampling_date": statistics["first_sample_date"],
                "latest_sampling_date": statistics["latest_sample_date"],
            }
        )
        # Earliest and Latest Genome Import
        earliest_genome_import = models.Sample.objects.order_by(
            "init_upload_date"
        ).first()
        latest_genome_import = models.Sample.objects.order_by(
            "-init_upload_date"
        ).first()

        result["earliest_genome_import"] = (
            earliest_genome_import.init_upload_date if earliest_genome_import else None
        )
        result["latest_genome_import"] = (
            latest_genome_import.init_upload_date if latest_genome_import else None
        )
        # Reference Genomes with organism-specific statistics
        result["reference_genomes"] = {}
        for reference in models.Reference.objects.all():
            organism = reference.organism
            if organism not in result["reference_genomes"]:
                result["reference_genomes"][organism] = {}
            replicons = models.Replicon.objects.filter(
                description__isnull=False, reference__accession=reference.accession
            )
            result["reference_genomes"][organism]["replicons"] = [
                f"{replicon.accession} {replicon.description}" for replicon in replicons
            ]
            result["reference_genomes"][organism]["reference_length"] = [
                reference_replicon.length for reference_replicon in replicons
            ]
            # Annotated Proteins
            annotated_proteins = models.Gene.objects.filter(
                cds__gene__symbol__isnull=False,
                cds__gene__replicon__reference__accession=reference.accession,
            ).values_list("symbol", flat=True)
            result["reference_genomes"][organism]["annotated_proteins"] = ", ".join(
                sorted(set(annotated_proteins))
            )

            # Unique Sequences for this organism
            unique_sequences = (
                models.Sequence.objects.filter(
                    alignments__replicon__reference__accession=reference.accession
                )
                .distinct()
                .count()
            )
            result["reference_genomes"][organism]["unique_sequences"] = unique_sequences

            # Total Genomes (alignments) for this organism
            total_genomes = models.Alignment.objects.filter(
                replicon__reference__accession=reference.accession
            ).count()
            result["reference_genomes"][organism]["genomes"] = total_genomes
        print(result["reference_genomes"])
        result["database_size"] = self.get_database_size()
        result["database_version"] = self.get_database_version()
        return Response(data={"detail": result}, status=status.HTTP_200_OK)

    def get_database_size(self):

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT pg_size_pretty(pg_database_size(current_database()));
            """
            )
            return cursor.fetchone()[0]

    def get_database_version(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            return cursor.fetchone()[0]
