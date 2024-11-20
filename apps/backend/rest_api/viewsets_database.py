from django.db import connection
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action

from rest_api.utils import Response
from . import models
from .viewsets_sample import SampleViewSet


class DatabaseInfoView(
    viewsets.GenericViewSet,
):
    @action(detail=False, methods=["get"])  # detail=False means it's a list action
    def get_database_info(self, request, *args, **kwargs):
        dict = {}
        queryset = SampleViewSet()._get_filtered_queryset(request)
        statistics = SampleViewSet.get_statistics()
        total_samples = statistics["samples_total"]
        meta_data_coverage = SampleViewSet()._get_meta_data_coverage(queryset)
        # Add percentages
        for key, count in meta_data_coverage.items():
            percentage = (count / total_samples) * 100 if total_samples > 0 else 0
            meta_data_coverage[key] = f"{count} ({percentage:.2f}%)"

        dict["meta_data_coverage"] = meta_data_coverage
        dict.update(
            {
                "samples_total": total_samples,
                "earliest_sampling_date": statistics["first_sample_date"],
                "latest_sampling_date": statistics["latest_sample_date"],
            }
        )

        dict["database_size"] = self.get_database_size()
        dict["database_version"] = self.get_database_version()
        # Earliest and Latest Genome Import
        earliest_genome_import = models.Sample.objects.order_by(
            "init_upload_date"
        ).first()
        latest_genome_import = models.Sample.objects.order_by(
            "-init_upload_date"
        ).first()

        dict["earliest_genome_import"] = (
            earliest_genome_import.init_upload_date if earliest_genome_import else None
        )
        dict["latest_genome_import"] = (
            latest_genome_import.init_upload_date if latest_genome_import else None
        )
        # Unique Sequences
        unique_sequences = models.Sequence.objects.count()
        dict["unique_sequences"] = unique_sequences
        # Total Genomes
        total_genomes = models.Alignment.objects.count()
        dict["genomes"] = total_genomes
        # Reference Genome
        reference_replicon = models.Replicon.objects.filter(
            description__isnull=False
        ).first()
        dict["reference_genome"] = (
            f"{reference_replicon.accession} {reference_replicon.description}"
            if reference_replicon
            else None
        )
        dict["reference_length"] = (
            reference_replicon.length if reference_replicon else None
        )
        # Annotated Proteins
        annotated_proteins = models.Gene.objects.filter(
            cds_symbol__isnull=False
        ).values_list("cds_symbol", flat=True)
        dict["annotated_proteins"] = ", ".join(sorted(set(annotated_proteins)))

        return Response(data={"detail": dict}, status=status.HTTP_200_OK)

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
