import ast
from collections import defaultdict
import csv
from dataclasses import dataclass
from datetime import datetime
import json
import os
import pathlib
import re
import traceback
from typing import Generator

import _csv
from dateutil.rrule import rrule
from dateutil.rrule import WEEKLY
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.paginator import Paginator
from django.db.models import Case
from django.db.models import Count
from django.db.models import IntegerField
from django.db.models import Min
from django.db.models import OuterRef
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Subquery
from django.db.models import When
from django.http import StreamingHttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response

from covsonar_backend.settings import DEBUG
from covsonar_backend.settings import LOGGER
from covsonar_backend.settings import SONAR_DATA_ENTRY_FOLDER
from rest_api.data_entry.sample_job import delete_sample
from rest_api.serializers import SampleGenomesExportStreamSerializer
from rest_api.serializers import SampleSerializer
from rest_api.utils import define_profile
from rest_api.utils import resolve_ambiguous_NT_AA
from rest_api.utils import Response
from rest_api.utils import strtobool
from rest_api.viewsets import get_distinct_gene_symbols
from rest_api.viewsets import PropertyViewSet
from . import models
from .serializers import SampleGenomesSerializer
from .serializers import SampleGenomesSerializerVCF
from .serializers import SampleSerializer


@dataclass
class LineageInfo:
    name: str
    parent: str

    def __hash__(self):
        return hash((self.name, self.parent))


class Echo:
    def write(self, value):
        return value


class SampleViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    queryset = models.Sample.objects.all().order_by("id")
    serializer_class = SampleSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    lookup_field = "name"
    filter_fields = ["name"]

    @property
    def filter_label_to_methods(self):
        return {
            "Property": self.filter_property,
            "SNP Nt": self.filter_snp_profile_nt,
            "SNP AA": self.filter_snp_profile_aa,
            "Del Nt": self.filter_del_profile_nt,
            "Del AA": self.filter_del_profile_aa,
            "Ins Nt": self.filter_ins_profile_nt,
            "Ins AA": self.filter_ins_profile_aa,
            "Replicon": self.filter_replicon,
            "Sample": self.filter_sample,
            "Lineages": self.filter_sublineages,
            "Annotation": self.filter_annotation,
            "DNA/AA Profile": self.filter_label,
        }

    @staticmethod
    def get_statistics():
        response_dict = {}
        response_dict["samples_total"] = models.Sample.objects.all().count()

        first_sample = (
            models.Sample.objects.filter(collection_date__isnull=False)
            .order_by("collection_date")
            .first()
        )
        response_dict["first_sample_date"] = (
            first_sample.collection_date if first_sample else None
        )

        latest_sample = (
            models.Sample.objects.filter(collection_date__isnull=False)
            .order_by("-collection_date")
            .first()
        )
        response_dict["latest_sample_date"] = (
            latest_sample.collection_date if latest_sample else None
        )
        return response_dict

    @action(detail=False, methods=["get"])
    def statistics(self, request: Request, *args, **kwargs):
        response_dict = SampleViewSet.get_statistics()
        return Response(data=response_dict, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def samples_per_day(self, request: Request, *args, **kwargs):
        queryset = (
            models.Sample.objects.values("collection_date")
            .annotate(count=Count("id"))
            .order_by("collection_date")
        )
        dict = {str(item["collection_date"]): item["count"] for item in queryset}
        return Response(data=dict)

    @action(detail=False, methods=["get"])
    def count_unique_nt_mut_ref_view_set(self, request: Request, *args, **kwargs):
        # TODO-smc abklären ob das so richtig ist
        queryset = (
            models.Mutation.objects.exclude(
                element__type="cds",
                alt="N",
            )
            .values("element__molecule__reference__accession")
            .annotate(count=Count("id"))
        )
        dict = {
            item["element__molecule__reference__accession"]: item["count"]
            for item in queryset
        }
        return Response(data=dict)

    def _get_filtered_queryset(self, request: Request):
        queryset = models.Sample.objects.all()
        if filter_params := request.query_params.get("filters"):
            filters = json.loads(filter_params)
            LOGGER.info(f"Genomes Query, conditions: {filters}")
            queryset = models.Sample.objects.filter(self.resolve_genome_filter(filters))

        return queryset

    @action(detail=False, methods=["get"])
    def genomes(self, request: Request, *args, **kwargs):
        """
        fetch samples and genomic profiles based on provided filters and optional parameters

        TODO:
        1. Optimize the query (reduce the database hit)
        2. add accession of reference at the output
        """
        try:
            timer = datetime.now()
            # optional query parameters
            # we try to use bool(), but it is not working as expected.
            showNX = strtobool(request.query_params.get("showNX", "False"))
            csv_stream = strtobool(request.query_params.get("csv_stream", "False"))
            vcf_format = strtobool(request.query_params.get("vcf_format", "False"))

            LOGGER.info(
                f"Genomes Query, optional parameters: showNX:{showNX} csv_stream:{csv_stream}"
            )

            self.has_property_filter = False

            queryset = self._get_filtered_queryset(request)

            # apply ID ('name') filter if provided
            if name_filter := request.query_params.get("name"):
                queryset = queryset.filter(name=name_filter)

            # fetch genomic and proteomic profiles
            genomic_profiles_qs = (
                models.Mutation.objects.filter(type="nt")
                .only("ref", "alt", "start", "end", "gene")
                .prefetch_related("gene")
                .order_by("start")
            )
            proteomic_profiles_qs = (
                models.Mutation.objects.filter(type="cds")
                .only("ref", "alt", "start", "end", "gene")
                .prefetch_related("gene")
                .order_by("gene", "start")
            )
            annotation_qs = models.Mutation2Annotation.objects.prefetch_related(
                "mutation", "annotation"
            )

            if DEBUG:
                LOGGER.info(queryset.query)

            # filter out ambiguous nucleotides or unspecified amino acids
            if not showNX:
                genomic_profiles_qs = genomic_profiles_qs.exclude(alt="N")
                proteomic_profiles_qs = proteomic_profiles_qs.exclude(alt="X")

            # optimize queryset by prefetching and storing profiles as attributes
            queryset = queryset.select_related("sequence").prefetch_related(
                "properties__property",
                Prefetch(
                    "sequence__alignments__mutations",
                    queryset=genomic_profiles_qs,
                    to_attr="genomic_profiles",
                ),
                Prefetch(
                    "sequence__alignments__mutations",
                    queryset=proteomic_profiles_qs,
                    to_attr="proteomic_profiles",
                ),
                Prefetch(
                    "sequence__alignments__mutation2annotation_set",
                    queryset=annotation_qs,
                    to_attr="alignment_annotations",
                ),
            )

            # apply ordering if specified
            ordering = request.query_params.get("ordering")
            if ordering:
                queryset = self._apply_ordering(queryset, ordering)
            # return csv stream if specified
            if csv_stream:
                if not ordering:
                    queryset.order_by("-collection_date")
                return self._return_csv_stream(queryset, request)

            # return vcf format if specified
            if vcf_format:
                return self._return_vcf_format(queryset)

            # default response
            queryset = self.paginate_queryset(queryset)
            LOGGER.info(
                f"Query time done in {datetime.now() - timer},Start to Format result"
            )
            serializer = SampleGenomesSerializer(queryset, many=True)
            timer = datetime.now()
            LOGGER.info(
                f"Serializer done in {datetime.now() - timer},Start to Format result"
            )
            return self.get_paginated_response(serializer.data)
        except ValueError as e:
            return Response(data={"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            return Response(
                data={"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _apply_ordering(self, queryset, ordering):
        """
        apply given ordering to queryset
        """
        property_names = PropertyViewSet.get_custom_property_names()
        ordering_col_name = ordering.lstrip("-")
        reverse_order = ordering.startswith("-")

        if ordering_col_name in property_names:
            datatype = models.Property.objects.get(name=ordering_col_name).datatype
            queryset = queryset.order_by(
                Subquery(
                    models.Sample2Property.objects.filter(
                        property__name=ordering_col_name, sample=OuterRef("id")
                    ).values(datatype)
                )
            )
            if reverse_order:
                queryset = queryset.reverse()
        else:
            queryset = queryset.order_by(ordering)

        return queryset

    def _return_csv_stream(self, queryset, request):
        """
        stream queryset data as a csv file
        """
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer, delimiter=";")
        columns = request.query_params.get("columns")

        if columns:
            columns = columns.split(",")
        else:
            raise Exception("No columns provided")

        filename = request.query_params.get(
            "filename", "sample_genomes.csv"
        )  # default: "sample_genomes.csv"

        return StreamingHttpResponse(
            self._stream_serialized_data(queryset, columns, writer),
            content_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def _return_vcf_format(self, queryset):
        """
        return queryset data in vcf format
        """
        queryset = self.paginate_queryset(queryset)
        serializer = SampleGenomesSerializerVCF(queryset, many=True)
        return self.get_paginated_response(serializer.data)

    def _stream_serialized_data(
        self, queryset: QuerySet, columns: list[str], writer: "_csv._writer"
    ) -> Generator:
        serializer = SampleGenomesExportStreamSerializer
        serializer.columns = columns
        # yield writer.writerow(columns)
        paginator = Paginator(queryset, 100)
        for page in paginator.page_range:
            for serialized in serializer(
                paginator.page(page).object_list, many=True
            ).data:
                yield writer.writerow(serialized["row"])

    def _get_meta_data_coverage(self, queryset):
        dict = {}
        queryset = queryset.prefetch_related("properties__property")
        annotations = {}
        # sample table meta data fields
        for field in models.Sample._meta.get_fields():
            if field.concrete and not field.is_relation:
                if field.name in ["id", "name", "datahash"]:
                    continue
                field_name = field.name
                annotations[f"not_null_count_{field_name}"] = Count(
                    Case(
                        When(**{f"{field_name}__isnull": False}, then=1),
                        output_field=IntegerField(),
                    )
                )
        # property table meta data fields
        property_to_datatype = {
            property.name: property.datatype
            for property in models.Property.objects.all()
        }
        property_names = PropertyViewSet.get_custom_property_names()
        for property_name in property_names:
            try:
                if property_name not in property_to_datatype:
                    print(f"Property {property_name} not found")
                    continue
                datatype = property_to_datatype[property_name]
                # Determine the exclusion value based on the datatype
                annotations[f"not_null_count_{property_name}"] = Count(
                    Subquery(
                        models.Sample.objects.filter(
                            properties__property__name=property_name,
                            **{f"properties__{datatype}__isnull": False},
                            id=OuterRef("id"),
                        ).values("id")[:1]
                    )
                )
            except ValueError as e:
                LOGGER.error(
                    f"Error with property_name: {property_name}, datatype: {datatype}"
                )
                LOGGER.error(f"Error message: {e}")

        # Use the aggregate method with the dynamically created dictionary
        result = queryset.aggregate(**annotations)

        # Print or use the result
        dict = {
            key.replace("not_null_count_", ""): value
            for key, value in result.items()
            if key.startswith("not_null_count")
        }

        return dict

    def _get_genomecomplete_chart(self, queryset):
        result_dict = {}
        grouped_queryset = (
            queryset.values("genome_completeness")
            .annotate(total=Count("genome_completeness"))
            .order_by()
        )
        result_dict = {
            item["genome_completeness"]: item["total"] for item in grouped_queryset
        }
        return result_dict

    def _get_length_chart(self, queryset):
        result_dict = {}
        grouped_queryset = (
            queryset.values("length").annotate(total=Count("length")).order_by()
        )
        result_dict = {item["length"]: item["total"] for item in grouped_queryset}
        return result_dict

    def _get_lab_chart(self, queryset):
        result_dict = {}
        grouped_queryset = (
            queryset.values("lab").annotate(total=Count("lab")).order_by()
        )
        result_dict = {item["lab"]: item["total"] for item in grouped_queryset}
        return result_dict

    def _get_host_chart(self, queryset):
        result_dict = {}
        grouped_queryset = (
            queryset.values("host").annotate(total=Count("host")).order_by()
        )
        result_dict = {item["host"]: item["total"] for item in grouped_queryset}
        return result_dict

    def _get_zip_code_chart(self, queryset):
        result_dict = {}
        grouped_queryset = (
            queryset.values("zip_code").annotate(total=Count("zip_code")).order_by()
        )
        result_dict = {item["zip_code"]: item["total"] for item in grouped_queryset}
        return result_dict

    def _get_sequencingReason_chart(self, queryset):
        result_dict = {}
        queryset = queryset.filter(properties__property__name="sequencing_reason")

        # the value_char" holds the sequencing reason values
        grouped_queryset = (
            queryset.values("properties__value_varchar")
            .annotate(total=Count("properties__value_varchar"))
            .order_by()
        )
        # grouped_queryset = queryset.values('sequencing_reason').annotate(total=Count('sequencing_reason')).order_by()
        result_dict = {
            item["properties__value_varchar"]: item["total"]
            for item in grouped_queryset
        }
        return result_dict

    def _get_sampleType_chart(self, queryset):
        result_dict = {}
        queryset = queryset.filter(properties__property__name="sample_type")

        # the value_char" holds the sample type values
        grouped_queryset = (
            queryset.values("properties__value_varchar")
            .annotate(total=Count("properties__value_varchar"))
            .order_by()
        )
        # grouped_queryset = queryset.values('sequencing_reason').annotate(total=Count('sequencing_reason')).order_by()
        result_dict = {
            item["properties__value_varchar"]: item["total"]
            for item in grouped_queryset
        }
        return result_dict

    def _get_sequencingTech_chart(self, queryset):
        result_dict = {}
        grouped_queryset = (
            queryset.values("sequencing_tech")
            .annotate(total=Count("sequencing_tech"))
            .order_by()
        )
        result_dict = {
            item["sequencing_tech"]: item["total"] for item in grouped_queryset
        }
        return result_dict

    def _get_samples_per_week(self, queryset):
        result_dict = {}
        queryset = (
            queryset.values("year", "week")
            .annotate(count=Count("id"), collection_date=Min("collection_date"))
            .order_by("year", "week")
        )
        if len(queryset) != 0:
            filtered_queryset = queryset.filter(collection_date__isnull=False)
            start_date = filtered_queryset.first()["collection_date"]
            end_date = filtered_queryset.last()["collection_date"]
            if start_date and end_date:
                for dt in rrule(
                    WEEKLY, dtstart=start_date, until=end_date
                ):  # generate all weeks between start and end dates and assign default value 0
                    result_dict[f"{dt.year}-W{dt.isocalendar()[1]:02}"] = 0
                for item in filtered_queryset:  # fill in count values of present weeks
                    result_dict[f"{item['year']}-W{int(item['week']):02}"] = item[
                        "count"
                    ]
        return result_dict

    def normalize_get_monthly_lineage_percentage_area_chart(self, queryset):
        monthly_data = (
            queryset.values("month", "year", "lineage", "lineage_parent")
            .annotate(lineage_count=Count("id"))
            .order_by("year", "month", "lineage")
        )

        # Organize monthly lineage data into a dictionary for processing
        lineage_data = defaultdict(lambda: defaultdict(int))
        for item in monthly_data:
            month_str = (
                f"{item['year']}-{str(item['month']).zfill(2)}"  # Format as "YYYY-MM"
            )
            lineage_data[month_str][
                LineageInfo(item["lineage"], item["lineage_parent"])
            ] += item["lineage_count"]

        result = []

        # Process each month to apply the 10% threshold-based grouping
        for month, lineages in lineage_data.items():
            total_count = sum(lineages.values())
            threshold_count = total_count * 0.10

            # Use the helper function for aggregation
            aggregated_lineages = aggregate_below_threshold_lineages(
                lineages, threshold_count
            )

            # Calculate percentages
            for lineage, count in aggregated_lineages.items():
                percentage = (count / total_count) * 100
                result.append(
                    {
                        "date": month,
                        "lineage": lineage,
                        "percentage": round(percentage, 2),
                    }
                )

        return result

    def get_monthly_lineage_percentage_area_chart(self, queryset: QuerySet):
        # Annotate each sample with the month based on collection_date
        monthly_data = (
            queryset.values("month", "lineage")
            .annotate(
                lineage_count=Count("id")
            )  # Count occurrences of each lineage per month
            .order_by("month", "lineage")
        )

        # Calculate total samples per month to determine percentages
        total_per_month = (
            queryset.values("month").annotate(total_count=Count("id")).order_by("month")
        )

        # Create a dictionary for quick lookup of total counts per month
        month_totals = {item["month"]: item["total_count"] for item in total_per_month}

        # Construct the final result with percentages
        result = []
        for item in monthly_data:
            if item["month"] is None:
                continue
            month_str = (
                f"{item['year']}-{str(item['month']).zfill(2)}"  # Format as "YYYY-MM"
            )
            percentage = (item["lineage_count"] / month_totals[item["month"]]) * 100
            result.append(
                {
                    "date": month_str,
                    "lineage": item["lineage"],
                    "percentage": round(percentage, 2),
                }
            )

        return result

    def normalize_get_weekly_lineage_percentage_bar_chart(self, queryset):
        # Annotate each sample with the start of the week and count occurrences per lineage
        weekly_data = (
            queryset.values("year", "week", "lineage", "lineage_parent")
            .annotate(lineage_count=Count("id"))
            .order_by("year", "week", "lineage")
        )

        # Organize lineage counts by week into a dictionary
        lineage_data = defaultdict(lambda: defaultdict(int))

        for item in weekly_data:
            if item["week"] is None:
                continue
            week_str = f"{item['year']}-W{int(item['week']):02}"  # Format as "YYYY-WXX"
            lineage_data[week_str][
                LineageInfo(item["lineage"], item["lineage_parent"])
            ] += item["lineage_count"]

        # Initialize final result list
        result = []

        # Process each week, applying the 10% threshold rule

        for week, lineages in lineage_data.items():
            total_count = sum(lineages.values())
            threshold_count = total_count * 0.10

            # Aggregate below-threshold lineages using the helper function
            aggregated_lineages = aggregate_below_threshold_lineages(
                lineages, threshold_count
            )

            # Calculate percentages
            for lineage, count in aggregated_lineages.items():
                percentage = (count / total_count) * 100
                result.append(
                    {
                        "week": week,
                        "lineage": lineage,
                        "percentage": round(percentage, 2),
                    }
                )

        return result

    def get_weekly_lineage_percentage_bar_chart(self, queryset):
        # Annotate each sample with the start of the week based on collection_date
        weekly_data = (
            queryset.values("week", "lineage")
            .annotate(
                lineage_count=Count("id")
            )  # Count occurrences of each lineage per week
            .order_by("week", "lineage")
        )

        # Calculate total samples per week to determine percentages
        total_per_week = (
            queryset.values("week").annotate(total_count=Count("id")).order_by("week")
        )

        # Create a dictionary for quick lookup of total counts per week
        week_totals = {item["week"]: item["total_count"] for item in total_per_week}

        # Construct the final result with percentages
        result = []
        for item in weekly_data:
            week_str = f"{item['year']}-W{int(item['week']):02}"  # Format as "YYYY-WXX"
            percentage = (item["lineage_count"] / week_totals[item["week"]]) * 100
            result.append(
                {
                    "week": week_str,
                    "lineage": item["lineage"],
                    "percentage": round(percentage, 2),
                }
            )

        return result

    @action(detail=False, methods=["get"])
    def filtered_statistics(self, request: Request, *args, **kwargs):
        queryset = self._get_filtered_queryset(request)
        queryset = queryset.annotate(
            lineage_parent=Subquery(
                models.Lineage.objects.filter(name=OuterRef("lineage")).values(
                    "parent"
                )[:1]
            )
        )
        queryset = queryset.extra(
            select={
                "week": 'EXTRACT(\'week\' FROM "sample"."collection_date")',
                "month": 'EXTRACT(\'month\' FROM "sample"."collection_date")',
                "year": 'EXTRACT(\'year\' FROM "sample"."collection_date")',
            }
        )
        dict = {}
        dict["filtered_total_count"] = queryset.count()
        dict["meta_data_coverage"] = self._get_meta_data_coverage(queryset)
        dict["samples_per_week"] = self._get_samples_per_week(queryset)
        dict["genomecomplete_chart"] = self._get_genomecomplete_chart(queryset)

        # dict["lineage_area_chart"] = self.get_monthly_lineage_percentage_area_chart(queryset)
        dict["lineage_area_chart"] = (
            self.normalize_get_monthly_lineage_percentage_area_chart(queryset)
        )
        dict["lineage_bar_chart"] = (
            self.normalize_get_weekly_lineage_percentage_bar_chart(queryset)
        )
        dict["sequencing_tech"] = self._get_sequencingTech_chart(queryset)
        dict["sequencing_reason"] = self._get_sequencingReason_chart(queryset)
        dict["sample_type"] = self._get_sampleType_chart(queryset)
        dict["host"] = self._get_host_chart(queryset)
        dict["length"] = self._get_length_chart(queryset)
        dict["lab"] = self._get_lab_chart(queryset)
        dict["zip_code"] = self._get_zip_code_chart(queryset)
        return Response(data=dict)

    def resolve_genome_filter(self, filters) -> Q:
        q_obj = Q()
        for filter in filters.get("andFilter", []):
            if "orFilter" in filter or "andFilter" in filter:
                q_obj &= self.resolve_genome_filter(filter)
            else:
                q_obj &= self.eval_basic_filter(q_obj, filter)
        if "label" in filters:
            q_obj &= self.eval_basic_filter(q_obj, filters)
        for or_filter in filters.get("orFilter", []):
            q_obj |= self.resolve_genome_filter(or_filter)
        return q_obj

    def eval_basic_filter(self, q_obj, filter):
        method = self.filter_label_to_methods.get(filter.get("label"))
        if method:
            q_obj = method(qs=q_obj, **filter)
        else:
            raise Exception(f"filter_method not found for:{filter.get('label')}")
        return q_obj

    @action(detail=True, methods=["get"])
    def get_all_sample_data(self, request: Request, *args, **kwargs):
        sample = self.get_object()
        serializer = SampleGenomesSerializer(sample)
        return Response(serializer.data)

    def filter_label(
        self,
        value,
        exclude: bool = False,
        *args,
        **kwargs,
    ):
        final_query = Q()

        # Split the input value by either commas, whitespace, or both
        # mutations  = [x.strip() for x in value.split(',')]
        mutations = re.split(r"[\s,]+", value.strip())
        for mutation in mutations:
            parsed_mutation = define_profile(mutation)
            # check valid protien name
            if (
                "protein_symbol" in parsed_mutation
                and parsed_mutation["protein_symbol"] not in get_distinct_gene_symbols()
            ):
                raise ValueError(
                    f"Invalid protein name: {parsed_mutation['protein_symbol']}."
                )
            # Check the parsed mutation type and call the appropriate filter function
            if parsed_mutation.get("label") == "SNP Nt":
                q_obj = self.filter_snp_profile_nt(
                    ref_nuc=parsed_mutation["ref_nuc"],
                    ref_pos=int(parsed_mutation["ref_pos"]),
                    alt_nuc=parsed_mutation["alt_nuc"],
                )

            elif parsed_mutation.get("label") == "SNP AA":
                q_obj = self.filter_snp_profile_aa(
                    protein_symbol=parsed_mutation["protein_symbol"],
                    ref_aa=parsed_mutation["ref_aa"],
                    ref_pos=int(parsed_mutation["ref_pos"]),
                    alt_aa=parsed_mutation["alt_aa"],
                )

            elif parsed_mutation.get("label") == "Del Nt":
                q_obj = self.filter_del_profile_nt(
                    first_deleted=parsed_mutation["first_deleted"],
                    last_deleted=parsed_mutation.get("last_deleted", ""),
                )

            elif parsed_mutation.get("label") == "Del AA":
                q_obj = self.filter_del_profile_aa(
                    protein_symbol=parsed_mutation["protein_symbol"],
                    first_deleted=parsed_mutation["first_deleted"],
                    last_deleted=parsed_mutation.get("last_deleted", ""),
                )

            elif parsed_mutation.get("label") == "Ins Nt":
                q_obj = self.filter_ins_profile_nt(
                    ref_nuc=parsed_mutation["ref_nuc"],
                    ref_pos=int(parsed_mutation["ref_pos"]),
                    alt_nuc=parsed_mutation["alt_nuc"],
                )

            elif parsed_mutation.get("label") == "Ins AA":
                q_obj = self.filter_ins_profile_aa(
                    protein_symbol=parsed_mutation["protein_symbol"],
                    ref_aa=parsed_mutation["ref_aa"],
                    ref_pos=int(parsed_mutation["ref_pos"]),
                    alt_aa=parsed_mutation["alt_aa"],
                )

            else:

                raise ValueError(
                    f"Unsupported mutation type: {parsed_mutation.get('label')}"
                )

            # Combine queries with AND operator (&) for each mutation
            final_query &= q_obj

        if exclude:
            final_query = ~final_query

        return final_query

    def filter_annotation(
        self,
        property_name,
        filter_type,
        value,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # if property_name == "impact":
        #     mutation_condition = Q(annotations__impact__{filter_type}"=ref_pos)
        # elif property_name == "seq_ontology":
        #     mutation_condition = Q(annotations__seq_ontology__{filter_type}"=ref_pos)
        query = {}
        query[f"mutation2annotation__annotation__{property_name}__{filter_type}"] = (
            value
        )

        alignment_qs = models.Alignment.objects.filter(**query)
        filters = {"sequence__alignments__in": alignment_qs}

        if exclude:
            return ~Q(**filters)
        return Q(**filters)

    def filter_property(
        self,
        property_name,
        filter_type,
        value,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # Convert str of list into list object
        # "['X','N']" -> ['X','N']
        if isinstance(value, str):
            try:
                # Safely evaluate the string representation of the list and convert it to a list object
                value = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                # Handle the case where the string couldn't be evaluated as a list
                pass

        # check the filter_type
        if filter_type == "contains":
            value = value.strip("%")
        elif filter_type == "range":
            if isinstance(value, str):
                value = value.split(",")

        self.has_property_filter = True
        if property_name in [field.name for field in models.Sample._meta.get_fields()]:
            query = {}
            query[f"{property_name}__{filter_type}"] = value
        else:
            datatype = models.Property.objects.get(name=property_name).datatype
            query = {f"properties__property__name": property_name}
            query[f"properties__{datatype}__{filter_type}"] = value
        if exclude:
            return ~Q(**query)
        return Q(**query)

    def filter_snp_profile_nt(
        self,
        # gene_symbol: str,
        ref_nuc: str,
        ref_pos: int,
        alt_nuc: str,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For NT: ref_nuc followed by ref_pos followed by alt_nuc (e.g. T28175C).
        # Create Q() objects for each condition
        if alt_nuc == "N":
            mutation_alt = Q()
            for x in resolve_ambiguous_NT_AA(type="nt", char=alt_nuc):
                mutation_alt = mutation_alt | Q(mutations__alt=x)
            # Unsupported lookup 'alt_in' for ForeignKey or join on the field not permitted.
            # mutation_alt = Q(
            #     mutations__alt_in=resolve_ambiguous_NT_AA(type="nt", char = alt_nuc)
            # )
        else:
            if alt_nuc == "n":
                alt_nuc = "N"

            mutation_alt = Q(mutations__alt=alt_nuc)
        mutation_condition = (
            Q(mutations__end=ref_pos)
            & Q(mutations__ref=ref_nuc)
            & (mutation_alt)
            & Q(mutations__type="nt")
        )
        alignment_qs = models.Alignment.objects.filter(mutation_condition)
        filters = {"sequence__alignments__in": alignment_qs}
        if exclude:
            return ~Q(**filters)
        return Q(**filters)

    def filter_snp_profile_aa(
        self,
        protein_symbol: str,
        ref_aa: str,
        ref_pos: str,
        alt_aa: str,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For AA: protein_symbol:ref_aa followed by ref_pos followed by alt_aa (e.g. OPG098:E162K)
        if protein_symbol not in get_distinct_gene_symbols():
            raise ValueError(f"Invalid protein name: {protein_symbol}.")
        if alt_aa == "X":
            mutation_alt = Q()
            for x in resolve_ambiguous_NT_AA(type="aa", char=alt_aa):
                mutation_alt = mutation_alt | Q(mutations__alt=x)
        else:
            if alt_aa == "x":
                alt_aa = "X"
            mutation_alt = Q(mutations__alt=alt_aa)

        mutation_condition = (
            Q(mutations__end=ref_pos)
            & Q(mutations__ref=ref_aa)
            & (mutation_alt)
            & Q(mutations__gene__gene_symbol=protein_symbol)
            & Q(mutations__type="cds")
        )
        alignment_qs = models.Alignment.objects.filter(mutation_condition)

        filters = {"sequence__alignments__in": alignment_qs}
        if exclude:
            return ~Q(**filters)
        return Q(**filters)

    def filter_del_profile_nt(
        self,
        first_deleted: str,
        last_deleted: str,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        """
        add new field exact match or not
        """
        # For NT: del:first_NT_deleted-last_NT_deleted (e.g. del:133177-133186).
        # in case only single deltion bp
        if last_deleted == "":
            last_deleted = first_deleted

        alignment_qs = models.Alignment.objects.filter(
            mutations__start=int(first_deleted) - 1,
            mutations__end=last_deleted,
            mutations__alt__isnull=True,
            mutations__type="nt",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        if exclude:
            return ~Q(**filters)
        return Q(**filters)

    def filter_del_profile_aa(
        self,
        protein_symbol: str,
        first_deleted: str,
        last_deleted: str,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For AA: protein_symbol:del:first_AA_deleted-last_AA_deleted (e.g. OPG197:del:34-35)
        if protein_symbol not in get_distinct_gene_symbols():
            raise ValueError(f"Invalid protein name: {protein_symbol}.")
        # in case only single deltion bp
        if last_deleted == "":
            last_deleted = first_deleted

        alignment_qs = models.Alignment.objects.filter(
            # search with case insensitive ORF1ab = orf1ab
            mutations__gene__gene_symbol__iexact=protein_symbol,
            mutations__start=int(first_deleted) - 1,
            mutations__end=last_deleted,
            mutations__alt__isnull=True,
            mutations__type="cds",
        )

        filters = {"sequence__alignments__in": alignment_qs}

        if exclude:
            return ~Q(**filters)
        return Q(**filters)

    def filter_ins_profile_nt(
        self,
        ref_nuc: str,
        ref_pos: int,
        alt_nuc: str,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For NT: ref_nuc followed by ref_pos followed by alt_nucs (e.g. T133102TTT)
        alignment_qs = models.Alignment.objects.filter(
            mutations__end=ref_pos,
            mutations__ref=ref_nuc,
            mutations__alt=alt_nuc,
            mutations__type="nt",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        if exclude:
            return ~Q(**filters)
        return Q(**filters)

    def filter_ins_profile_aa(
        self,
        protein_symbol: str,
        ref_aa: str,
        ref_pos: int,
        alt_aa: str,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For AA: protein_symbol:ref_aa followed by ref_pos followed by alt_aas (e.g. OPG197:A34AK)
        if protein_symbol not in get_distinct_gene_symbols():
            raise ValueError(f"Invalid protein name: {protein_symbol}.")
        alignment_qs = models.Alignment.objects.filter(
            mutations__end=ref_pos,
            mutations__ref=ref_aa,
            mutations__alt=alt_aa,
            mutations__gene__gene_symbol=protein_symbol,
            mutations__type="cds",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        if exclude:
            return ~Q(**filters)
        return Q(**filters)

    def filter_sample(
        self,
        value: str,
        exclude: bool = False,
        *args,
        **kwargs,
    ):
        if isinstance(value, str):
            sample_list = ast.literal_eval(value)
        else:
            sample_list = value

        if exclude:
            return ~Q(name__in=sample_list)
        else:
            return Q(name__in=sample_list)

    def filter_replicon(
        self,
        accession,
        exclude: bool = False,
        *args,
        **kwargs,
    ):
        if exclude:
            return ~Q(sequence__alignments__replicon__reference__accession=accession)
        else:
            return Q(sequence__alignments__replicon__reference__accession=accession)

    def filter_sublineages(
        self,
        lineageList,
        exclude: bool = False,
        includeSublineages: bool = True,
        *args,
        **kwargs,
    ):
        if isinstance(lineageList, str):
            lineageList = [lineageList]  # convert to list if a single string is passed

        lineages = models.Lineage.objects.filter(name__in=lineageList)

        if not lineages.exists():
            raise Exception(f"Lineage {lineages} not found.")
        if includeSublineages:
            sublineages = []
            for l in lineages:
                sublineages.extend(l.get_sublineages())
        else:
            sublineages = list(lineages)

        # match for all sublineages of all given lineages
        return self.filter_property(
            "lineage",
            "in",
            sublineages,
            exclude,
        )

    def _convert_date(self, date: str):
        datetime_obj = datetime.strptime(date, "%Y-%m-%d %H:%M:%S %z")
        return datetime_obj.date()

    # @action(detail=False, methods=["post"])
    # def import_properties_tsv(self, request: Request, *args, **kwargs):
    #     """
    #     NOTE:
    #     1. if prop is not exist in the database, it will not be created automatically
    #     """
    #     print("Importing properties...")
    #     timer = datetime.now()
    #     sample_id_column = request.data.get("sample_id_column")

    #     column_mapping = self._convert_property_column_mapping(
    #         json.loads(request.data.get("column_mapping"))
    #     )
    #     if not sample_id_column:
    #         return Response(
    #             {"detail": "No sample_id_column is provided"},
    #             status=status.HTTP_400_BAD_REQUEST,
    #         )
    #     if not column_mapping:
    #         return Response(
    #             {"detail": "No column_mapping is provided, nothing to import."},
    #             status=status.HTTP_200_OK,
    #         )

    #     if not request.FILES or "properties_tsv" not in request.FILES:
    #         return Response("No file uploaded.", status=400)

    #     tsv_file = request.FILES.get("properties_tsv")
    #     # Determine the separator based on the file extension
    #     file_name = tsv_file.name.lower()
    #     if file_name.endswith(".csv"):
    #         sep = ","
    #     elif file_name.endswith(".tsv"):
    #         sep = "\t"
    #     else:
    #         return Response(
    #             {"detail": "Unsupported file format, please upload a CSV or TSV file."},
    #             status=status.HTTP_400_BAD_REQUEST,
    #         )
    #     self._temp_save_file(tsv_file)
    #     return Response(
    #         {"detail": "File uploaded successfully"}, status=status.HTTP_201_CREATED
    #     )

    def _import_tsv(self, file_path):
        header = None
        with open(file_path, "r") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if not header:
                    header = row
                else:
                    yield dict(zip(header, row))

    def _temp_save_file(self, uploaded_file: InMemoryUploadedFile):
        file_path = os.path.join(SONAR_DATA_ENTRY_FOLDER, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        return file_path

    @action(detail=False, methods=["get"])
    def get_sample_data(self, request: Request, *args, **kwargs):
        sample_name = request.GET.get("sample_data")
        if not sample_name:
            return Response(
                {"detail": "Sample name is missing"}, status=status.HTTP_400_BAD_REQUEST
            )
        sample_model = (
            models.Sample.objects.filter(name=sample_name)
            .extra(select={"sample_id": "sample.id"})
            .values("sample_id", "name", "sequence__seqhash")
        )
        if sample_model:
            sample_data = list(sample_model)[0]
            if len(sample_model) > 1:
                # Not sure ....---
                print("more than one sample was using same name.")
        else:
            print("Cannot find:", sample_name)
            sample_data = {}

        return Response(data=sample_data)

    @action(detail=False, methods=["post"])
    def get_bulk_sample_data(self, request: Request, *args, **kwargs):
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body.decode("utf-8"))
            # example to be parsed data: {"sample_data": ["IMS-SEQ-01", "IMS-SEQ-04", "value3"]}
            sample_data_list = data.get("sample_data", [])
            sample_model = (
                models.Sample.objects.filter(name__in=sample_data_list)
                .extra(select={"sample_id": "sample.id"})
                .values("sample_id", "name", "sequence__seqhash")
            )
            # Convert the QuerySet to a list of dictionaries
            sample_data = list(sample_model)

            # Check for missing samples and add them to the result
            missing_samples = set(sample_data_list) - set(
                item["name"] for item in sample_data
            )
            for missing_sample in missing_samples:
                sample_data.append(
                    {
                        "sample_id": None,
                        "name": missing_sample,
                        "sequence__seqhash": None,
                    }
                )

            return Response(sample_data, status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response(
                {"detail": "Invalid JSON data / structure"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def delete_sample_data(self, request: Request, *args, **kwargs):
        sample_data = {}
        reference_accession = request.data.get("reference_accession", "")
        sample_list = json.loads(request.data.get("sample_list"))
        if DEBUG:
            print("Reference Accession:", reference_accession)
            print("Sample List:", sample_list)

        sample_data = delete_sample(sample_list=sample_list)

        return Response(data=sample_data)


class SampleGenomeViewSet(viewsets.GenericViewSet, generics.mixins.ListModelMixin):
    queryset = models.Sample.objects.all()
    serializer_class = SampleGenomesSerializer

    @action(detail=False, methods=["get"])
    def match(self, request: Request, *args, **kwargs):
        profile_filters = request.query_params.getlist("profile_filters")
        param_filters = request.query_params.getlist("param_filters")

    @action(detail=False, methods=["get"])
    def test_profile_filters():
        pass


def aggregate_below_threshold_lineages(lineages, threshold_count):
    """
    Aggregates below-threshold lineages by recursively moving counts up the lineage hierarchy
    until they meet or exceed the specified threshold.

    :param lineages: A dictionary with lineage names as keys and counts as values.
    :param threshold_count: The threshold count (10% of total samples).
    :return: A dictionary with lineages aggregated above the threshold.
    """
    above_threshold = {
        lineage.name: count
        for lineage, count in lineages.items()
        if count >= threshold_count
    }
    below_threshold = {
        lineage: count for lineage, count in lineages.items() if count < threshold_count
    }

    for lineage, count in below_threshold.items():
        # Aggregate each below-threshold lineage recursively

        if lineage.parent:
            above_threshold[lineage.parent] = (
                above_threshold.get(lineage.parent, 0) + count
            )
        else:
            # If lineage has no parent, keep it as is
            above_threshold[lineage.name] = above_threshold.get(lineage.name, 0) + count

    return above_threshold
