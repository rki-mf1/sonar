import _csv
import ast
from collections import OrderedDict
import csv
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
import json
import os
import re
import traceback
from typing import Generator

from dateutil.rrule import rrule
from dateutil.rrule import WEEKLY
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.paginator import Paginator
from django.db.models import BooleanField
from django.db.models import Case
from django.db.models import CharField
from django.db.models import Count
from django.db.models import Exists
from django.db.models import IntegerField
from django.db.models import Max
from django.db.models import Min
from django.db.models import OuterRef
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Subquery
from django.db.models import Value
from django.db.models import When
from django.db.models.functions import TruncWeek
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
from rest_api.customDRF import CachedCountLimitOffsetPagination
from rest_api.customDRF import SerializedOutputCachePagination
from rest_api.data_entry.sample_job import delete_sample
from rest_api.serializers import SampleGenomesExportStreamSerializer
from rest_api.serializers import SampleSerializer
from rest_api.utils import define_profile
from rest_api.utils import get_distinct_gene_symbols
from rest_api.utils import resolve_ambiguous_NT_AA
from rest_api.utils import Response
from rest_api.utils import strtobool
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
    pagination_class = SerializedOutputCachePagination
    # CachedCountLimitOffsetPagination (good one)

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
            "Reference": self.filter_reference,
            "Sample": self.filter_sample,
            "Lineages": self.filter_sublineages,
            "Annotation": self.filter_annotation,
            "DNA/AA Profile": self.filter_label,
        }

    @staticmethod
    def get_statistics(reference=None):
        response_dict = {}
        queryset = models.Sample.objects.all()
        if reference:
            queryset = queryset.filter(
                sequence__alignments__replicon__reference__accession=reference
            )
        response_dict["samples_total"] = queryset.count()

        first_sample = (
            queryset.filter(collection_date__isnull=False)
            .order_by("collection_date")
            .first()
        )
        response_dict["first_sample_date"] = (
            first_sample.collection_date if first_sample else None
        )

        latest_sample = (
            queryset.filter(collection_date__isnull=False)
            .order_by("-collection_date")
            .first()
        )
        response_dict["latest_sample_date"] = (
            latest_sample.collection_date if latest_sample else None
        )
        response_dict["populated_metadata_fields"] = (
            SampleViewSet.get_populated_metadata_fields(queryset=queryset)
        )

        return response_dict

    @action(detail=False, methods=["get"])
    def statistics(self, request: Request, *args, **kwargs):
        response_dict = SampleViewSet.get_statistics(
            reference=request.query_params.get("reference")
        )
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
        fetch proteomic and genomic profiles based on provided filters and optional parameters

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
            genomic_profiles_qs = models.NucleotideMutation.objects.only(
                "ref", "alt", "start", "end"
            ).order_by("start")
            proteomic_profiles_qs = (
                models.AminoAcidMutation.objects.only(
                    "ref", "alt", "start", "end", "cds"
                )
                .prefetch_related("cds__cds_segments")
                .order_by("cds", "start")
            )
            annotation_qs = models.AnnotationType.objects.prefetch_related("mutations")

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
                    "sequence__alignments__nucleotide_mutations",
                    queryset=genomic_profiles_qs,
                    to_attr="genomic_profiles",
                ),
                Prefetch(
                    "sequence__alignments__amino_acid_mutations",
                    queryset=proteomic_profiles_qs,
                    to_attr="proteomic_profiles",
                ),
                Prefetch(
                    "sequence__alignments__nucleotide_mutations__annotations",
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

            # Cache check happens here
            queryset = self.paginate_queryset(queryset)
            LOGGER.info(
                f"Query time done in {datetime.now() - timer},Start to Format result"
            )
            serializer = SampleGenomesSerializer(queryset, many=True)
            timer = datetime.now()
            LOGGER.info(
                f"Serializer done in {datetime.now() - timer},Start to Format result"
            )
            # Caching happens here
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

    @staticmethod
    def get_populated_metadata_fields(queryset):
        queryset = queryset.prefetch_related("properties__property")
        annotations = {}

        # check genomic profiles
        annotations["has_genomic_profiles"] = Exists(
            models.Sample.objects.filter(
                sequence__alignments__nucleotide_mutations__isnull=False,
                id=OuterRef("id"),
            )
        )

        # check proteomic profiles
        annotations["has_proteomic_profiles"] = Exists(
            models.Sample.objects.filter(
                sequence__alignments__amino_acid_mutations__isnull=False,
                id=OuterRef("id"),
            )
        )

        # check sample fields
        for field in models.Sample._meta.get_fields():
            if field.concrete and not field.is_relation:
                field_name = field.name
                if field.get_internal_type() == "CharField":
                    condition = Q(**{f"{field_name}__isnull": False}) & ~Q(
                        **{field_name: ""}
                    )
                else:
                    condition = Q(**{f"{field_name}__isnull": False})

                annotations[f"has_{field_name}"] = Case(
                    When(condition, then=True),
                    default=False,
                    output_field=BooleanField(),
                )

        # check properties
        property_to_datatype = dict(
            models.Property.objects.values_list("name", "datatype")
        )
        for property_name in PropertyViewSet.get_custom_property_names():
            datatype = property_to_datatype.get(property_name)
            if not datatype:
                LOGGER.warning(f"Property {property_name} not found")
                continue

            try:
                annotations[f"has_{property_name}"] = Exists(
                    models.Sample.objects.filter(
                        id=OuterRef("id"),
                        properties__property__name=property_name,
                        **{f"properties__{datatype}__isnull": False},
                    )
                )
            except Exception as e:
                LOGGER.error(
                    f"Error processing property {property_name} (datatype: {datatype}): {e}"
                )

        # apply annotations and check existence (True/False)
        result = queryset.annotate(**annotations).values(*annotations.keys()).first()

        return (
            [k.replace("has_", "") for k in filter(result.get, result)]
            if result
            else []
        )

    @staticmethod
    def get_metadata_coverage(queryset):
        queryset = queryset.prefetch_related("properties__property")
        annotations = {}

        def add_annotation(name, filter_kwargs):
            annotations[f"not_null_count_{name}"] = Count(
                Case(
                    When(
                        Exists(
                            models.Sample.objects.filter(
                                id=OuterRef("id"), **filter_kwargs
                            )
                        ),
                        then=1,
                    ),
                    output_field=IntegerField(),
                )
            )

        # check genomic and proteomic profiles
        add_annotation(
            "genomic_profiles",
            {"sequence__alignments__nucleotide_mutations__isnull": False},
        )
        add_annotation(
            "proteomic_profiles",
            {"sequence__alignments__amino_acid_mutations__isnull": False},
        )

        for field in models.Sample._meta.get_fields():
            if field.concrete and not field.is_relation:
                field_name = field.name
                if field.get_internal_type() == "CharField":
                    condition = Q(**{f"{field_name}__isnull": False}) & ~Q(
                        **{field_name: ""}
                    )
                else:
                    condition = Q(**{f"{field_name}__isnull": False})

                annotations[f"not_null_count_{field_name}"] = Count(
                    Case(When(condition, then=1), output_field=IntegerField())
                )

        # mapping from property name to datatype
        property_to_datatype = dict(
            models.Property.objects.values_list("name", "datatype")
        )
        property_names = PropertyViewSet.get_custom_property_names()
        # annotate custom properties based on datatype
        for property_name in property_names:
            datatype = property_to_datatype.get(property_name)
            if not datatype:
                LOGGER.warning(f"Property {property_name} not found")
                continue
            try:
                annotations[f"not_null_count_{property_name}"] = Count(
                    Case(
                        When(
                            Exists(
                                models.Sample.objects.filter(
                                    id=OuterRef("id"),
                                    properties__property__name=property_name,
                                    **{f"properties__{datatype}__isnull": False},
                                )
                            ),
                            then=1,
                        ),
                        output_field=IntegerField(),
                    )
                )
            except Exception as e:
                LOGGER.error(
                    f"Error with property {property_name} (datatype: {datatype}): {e}"
                )

        result = queryset.aggregate(**annotations)
        return {
            key.replace("not_null_count_", ""): value
            for key, value in result.items()
            if key.startswith("not_null_count_")
        }

    @action(detail=False, methods=["get"])
    def distinct_lineages(self, request: Request, *args, **kwargs):
        queryset = models.Sample.objects.values_list("lineage", flat=True)
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(
                sequence__alignments__replicon__reference__accession=ref
            )
        distinct_lineages = queryset.distinct()

        return Response(
            {"lineages": distinct_lineages},
            status=status.HTTP_200_OK,
        )

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

    def _get_custom_property_plot(self, queryset, sample_property):
        if sample_property == "":
            result_dict = {}
        elif sample_property == "sequencing_reason":
            queryset = queryset.filter(properties__property__name="sequencing_reason")
            # the value_char holds the sequencing reason values
            grouped_queryset = (
                queryset.values("properties__value_varchar")
                .annotate(total=Count("properties__value_varchar"))
                .order_by()
            )
            result_dict = {
                item["properties__value_varchar"]: item["total"]
                for item in grouped_queryset
            }

        else:
            grouped_queryset = (
                queryset.values(sample_property)
                .annotate(total=Count(sample_property))
                .order_by(sample_property)
            )
            result_dict = {
                str(item[sample_property]): item["total"] for item in grouped_queryset
            }  # str required for properties in date format
        return result_dict

    def _get_samples_per_week(self, queryset):
        """
        Return a dict mapping calendar week to count, for each week between
        the earliest and latest collection_date.
        Weeks with zero records will be present with value 0.
        """

        weekly_qs = (
            queryset.annotate(week=TruncWeek("collection_date"))
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )

        result = {}
        for item in weekly_qs:
            year, week, _ = item["week"].isocalendar()
            result[f"{year}-W{week:02}"] = item["count"]

        return result

    def _get_grouped_lineages_per_week(self, queryset):
        """
        Return a LIST of dicts, contianing counts and percentages per calendar week for
        lineage groups (lineages truncated to two first segments),
        covering every week between the earliest and latest record.
        Weeks with zero records will be present with values 0.
        """
        present_lineages = set(
            queryset.exclude(lineage__isnull=True).values_list("lineage", flat=True)
        )
        lineage_to_group = {
            lineage: ".".join(lineage.split(".")[:2]) for lineage in present_lineages
        }
        valid_groups = set(
            models.Lineage.objects.filter(name__isnull=False).values_list(
                "name", flat=True
            )
        )
        lineage_cases = [
            When(lineage=lineage, then=Value(group))
            for lineage, group in lineage_to_group.items()
            if group in valid_groups
        ]
        annotated_qs = queryset.annotate(
            lineage_group=Case(
                *lineage_cases,
                default=Value("Unknown"),
                output_field=CharField(),
            ),
            week=TruncWeek("collection_date"),
        )

        weekly_qs = annotated_qs.values("week", "lineage_group").annotate(
            count=Count("id")
        )

        total_qs = annotated_qs.values("week").annotate(total_count=Count("id"))

        # lookup for total counts
        week_to_total = {entry["week"]: entry["total_count"] for entry in total_qs}

        result = []
        for item in weekly_qs:
            year, week, _ = item["week"].isocalendar()
            week_str = f"{year}-W{week:02}"
            total = week_to_total.get(item["week"])
            result.append(
                {
                    "week": week_str,
                    "lineage_group": item["lineage_group"],
                    "count": item["count"],
                    "percentage": round(item["count"] / total * 100, 2),
                }
            )

        result.sort(key=lambda x: x["week"])
        return result

    def _get_custom_property_plot(self, queryset, property):
        if property == "":
            result_dict = {}
        elif property == "sequencing_reason":
            queryset = queryset.filter(properties__property__name="sequencing_reason")
            # the value_char holds the sequencing reason values
            grouped_queryset = (
                queryset.values("properties__value_varchar")
                .annotate(total=Count("properties__value_varchar"))
                .order_by()
            )
            result_dict = {
                item["properties__value_varchar"]: item["total"]
                for item in grouped_queryset
            }

        else:
            grouped_queryset = (
                queryset.values(property)
                .annotate(total=Count(property))
                .order_by(property)
            )
            result_dict = {
                str(item[property]): item["total"] for item in grouped_queryset
            }  # str required for properties in date format

        return result_dict

    @action(detail=False, methods=["get"])
    def filtered_statistics(self, request: Request, *args, **kwargs):
        queryset = self._get_filtered_queryset(request)

        result_dict = {}
        result_dict["filtered_total_count"] = queryset.count()

        return Response(data=result_dict)

    @action(detail=False, methods=["get"])
    def plot_samples_per_week(self, request: Request, *args, **kwargs):
        queryset = self._get_filtered_queryset(request).filter(
            collection_date__isnull=False
        )

        if not queryset.exists():
            return Response(data=[])
        else:
            samples_per_week = self._get_samples_per_week(queryset)
            return Response(data=list(samples_per_week.items()))

    @action(detail=False, methods=["get"])
    def plot_grouped_lineages_per_week(self, request: Request, *args, **kwargs):
        queryset = self._get_filtered_queryset(request).filter(
            collection_date__isnull=False
        )

        result_dict = {}
        if not queryset.exists():
            result_dict["grouped_lineages_per_week"] = {}
        else:
            result_dict["grouped_lineages_per_week"] = (
                self._get_grouped_lineages_per_week(queryset)
            )

        return Response(data=result_dict)

    @action(detail=False, methods=["get"])
    def plot_metadata_coverage(self, request: Request, *args, **kwargs):
        queryset = self._get_filtered_queryset(request)

        result_dict = {}
        result_dict["metadata_coverage"] = SampleViewSet.get_metadata_coverage(queryset)
        return Response(data=result_dict)

    @action(detail=False, methods=["get"])
    def plot_custom(self, request: Request, *args, **kwargs):
        queryset = self._get_filtered_queryset(request)
        sample_property = request.query_params["property"]

        result_dict = {}
        result_dict[sample_property] = self._get_custom_property_plot(
            queryset, sample_property
        )
        return Response(data=result_dict)

    @action(detail=False, methods=["get"])
    def plot_custom_xy(self, request: Request, *args, **kwargs):
        """
        API call to plot data based on two properties: x and y categories.
        Handles both flexible properties (sample2property table) and fixed sample table properties.
        Returns:
            - For string-type y property: dict with x categories as keys and lists of y categories with counts.
            - For number-type y property: dict with x categories as keys and lists of y numbers.
        """
        queryset = self._get_filtered_queryset(request)
        x_property = request.query_params.get("x_property")
        y_property = request.query_params.get("y_property")

        if not x_property or not y_property:
            return Response(
                {"detail": "Both x_property and y_property must be provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Determine if x_property and y_property are flexible or fixed
        flexible_properties = PropertyViewSet.get_custom_property_names()
        x_is_flexible = x_property in flexible_properties
        y_is_flexible = y_property in flexible_properties

        result_dict = {}

        if y_is_flexible:
            # Handle flexible y_property
            y_datatype = (
                models.Property.objects.filter(name=y_property)
                .values_list("datatype", flat=True)
                .first()
            )

            if not y_datatype:
                return Response(
                    {"detail": f"Property {y_property} not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if x_is_flexible:
                # Both x_property and y_property are flexible
                grouped_queryset = (
                    queryset.filter(
                        properties__property__name__in=[x_property, y_property],
                        properties__value_varchar__isnull=False,
                        **{f"properties__{y_datatype}__isnull": False},
                    )
                    .values(
                        "properties__value_varchar",
                        f"properties__{y_datatype}",
                    )
                    .annotate(total=Count(f"properties__{y_datatype}"))
                    .order_by("properties__value_varchar", f"properties__{y_datatype}")
                )
                for item in grouped_queryset:
                    x_cat = str(item["properties__value_varchar"])
                    y_cat = str(item[f"properties__{y_datatype}"])
                    count = item["total"]
                    if x_cat not in result_dict:
                        result_dict[x_cat] = []
                    result_dict[x_cat].append({y_cat: count})

            else:
                # x_property is fixed, y_property is flexible
                grouped_queryset = (
                    queryset.filter(
                        **{f"{x_property}__isnull": False},
                        properties__property__name=y_property,
                        **{f"properties__{y_datatype}__isnull": False},
                    )
                    .values(x_property, f"properties__{y_datatype}")
                    .annotate(total=Count(f"properties__{y_datatype}"))
                    .order_by(x_property, f"properties__{y_datatype}")
                )
                for item in grouped_queryset:
                    x_cat = str(item[x_property])
                    y_cat = str(item[f"properties__{y_datatype}"])
                    count = item["total"]
                    if x_cat not in result_dict:
                        result_dict[x_cat] = []
                    result_dict[x_cat].append({y_cat: count})

        else:
            # Handle fixed y_property
            if x_is_flexible:
                # x_property is flexible, y_property is fixed
                grouped_queryset = (
                    queryset.filter(
                        properties__property__name=x_property,
                        **{f"{y_property}__isnull": False},
                        properties__value_varchar__isnull=False,
                    )
                    .values("properties__value_varchar", y_property)
                    .annotate(total=Count(y_property))
                    .order_by("properties__value_varchar", y_property)
                )
                for item in grouped_queryset:
                    x_cat = str(item["properties__value_varchar"])
                    y_cat = str(item[y_property])
                    count = item["total"]
                    if x_cat not in result_dict:
                        result_dict[x_cat] = []
                    result_dict[x_cat].append({y_cat: count})

            else:
                # Both x_property and y_property are fixed
                grouped_queryset = (
                    queryset.filter(
                        **{f"{x_property}__isnull": False},
                        **{f"{y_property}__isnull": False},
                    )
                    .values(x_property, y_property)
                    .annotate(total=Count(y_property))
                    .order_by(x_property, y_property)
                )
                for item in grouped_queryset:
                    x_cat = str(item[x_property])
                    y_cat = str(item[y_property])
                    count = item["total"]
                    if x_cat not in result_dict:
                        result_dict[x_cat] = []
                    result_dict[x_cat].append({y_cat: count})

        return Response(data=result_dict)

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

        # Split the input value by either commas, semicolom, whitespace, or combinations of these,
        # remove seperators from string end
        mutations = re.split(r"[,\s;]+", value.strip(",; \t\r\n"))
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
        query = {}
        query[f"nucleotide_mutations__annotations__{property_name}__{filter_type}"] = (
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

            mutation_alt = Q(nucleotide_mutations__alt=alt_nuc)
        mutation_condition = (
            Q(nucleotide_mutations__end=ref_pos)
            & Q(nucleotide_mutations__ref=ref_nuc)
            & (mutation_alt)
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
                mutation_alt = mutation_alt | Q(amino_acid_mutations__alt=x)
        else:
            if alt_aa == "x":
                alt_aa = "X"
            mutation_alt = Q(amino_acid_mutations__alt=alt_aa)

        mutation_condition = (
            Q(amino_acid_mutations__end=ref_pos)
            & Q(amino_acid_mutations__ref=ref_aa)
            & (mutation_alt)
            & Q(amino_acid_mutations__cds__gene__symbol=protein_symbol)
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
            nucleotide_mutations__start=int(first_deleted) - 1,
            nucleotide_mutations__end=last_deleted,
            nucleotide_mutations__alt="",
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
            amino_acid_mutations__cds__gene__symbol__iexact=protein_symbol,
            amino_acid_mutations__start=int(first_deleted) - 1,
            amino_acid_mutations__end=last_deleted,
            amino_acid_mutations__alt="",
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
            nucleotide_mutations__end=ref_pos,
            nucleotide_mutations__ref=ref_nuc,
            nucleotide_mutations__alt=alt_nuc,
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
            amino_acid_mutations__end=ref_pos,
            amino_acid_mutations__ref=ref_aa,
            amino_acid_mutations__alt=alt_aa,
            amino_acid_mutations__cds__gene__symbol=protein_symbol,
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
            return ~Q(sequence__alignments__replicon__accession=accession)
        else:
            return Q(sequence__alignments__replicon__accession=accession)

    def filter_reference(
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
            # band-aid, not perfect fix for not delivering ids instead of names
            parent_obj = models.Lineage.objects.get(id=lineage.parent)
            above_threshold[parent_obj.name] = (
                above_threshold.get(parent_obj.name, 0) + count
            )
        else:
            # If lineage has no parent, keep it as is
            above_threshold[lineage.name] = above_threshold.get(lineage.name, 0) + count

    return above_threshold
