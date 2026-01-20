import hashlib
import json

from django.core.cache import cache
from django.db.models import BooleanField
from django.db.models import Case
from django.db.models import CharField
from django.db.models import Count
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Value
from django.db.models import When
from django.db.models.functions import TruncWeek
from rest_framework import generics
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from covsonar_backend.settings import CACHE_OBJECT_TTL
from covsonar_backend.settings import LOGGER
from rest_api.viewsets import PropertyViewSet
from rest_api.viewsets_sample import SampleFilterMixin
from . import models


class SampleViewSetStatistics(
    SampleFilterMixin,
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    @staticmethod
    def get_statistics(reference=None):
        response_dict = {}
        queryset = models.Sample.objects.all()
        if reference:
            queryset = queryset.filter(
                sequences__alignments__replicon__reference__accession=reference
            ).distinct()
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
            SampleViewSetStatistics().get_populated_metadata_fields(queryset=queryset)
        )

        return response_dict

    @staticmethod
    def get_populated_metadata_fields(queryset):
        queryset = queryset.prefetch_related("properties__property")
        annotations = {}

        # check profiles was removed becasue it is slow and because these fields
        # are basically always populated

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

    @action(detail=False, methods=["get"])
    def statistics(self, request: Request, *args, **kwargs):
        response_dict = self.get_statistics(
            reference=request.query_params.get("reference")
        )
        return Response(data=response_dict, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def filtered_statistics(self, request: Request, *args, **kwargs):
        queryset = self.get_filtered_queryset(request)

        result_dict = {}
        result_dict["filtered_total_count"] = queryset.count()

        return Response(data=result_dict)


class SampleViewSetPlots(
    SampleFilterMixin,
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    @staticmethod
    def get_metadata_coverage(queryset):
        """
        Return a dict with counts of non-null values for each metadata field.

        Performance optimized:
        - Separate queries instead of massive aggregate()
        - Leverages Django's query optimization and JOIN handling
        - Caching of results for repeated queries

        Example output:{
            "metadata_coverage": {
                "id": 17942,
                "name": 17942,
                "lineage": 17942,
                "genome_completeness": 0,
                "collection_date": 17942,
                .....
                "last_update_date": 17942,
                "genomic_profiles": 17942,
                "proteomic_profiles": 17941
            }
        }
        """
        # STEP 1: Cache check - return immediately if cached
        queryset_sql = str(queryset.query)
        cache_key = (
            f"metadata_coverage:{hashlib.md5(queryset_sql.encode()).hexdigest()}"
        )

        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Initialize result dictionary
        final_result = {}

        # STEP 2: Count Sample table fields separately
        # Instead of building 12+ annotations, query each field individually
        # Django optimizes each query better than one massive aggregate()

        for field in models.Sample._meta.get_fields():
            if field.concrete and not field.is_relation:
                field_name = field.name

                try:
                    if field.get_internal_type() == "CharField":
                        # Count non-null AND non-empty strings
                        # Django will use the existing queryset filter + add this condition
                        count = (
                            queryset.filter(**{f"{field_name}__isnull": False})
                            .exclude(**{field_name: ""})
                            .values("id")
                            .distinct()
                            .count()
                        )
                    else:
                        # Count non-null values only
                        count = (
                            queryset.filter(**{f"{field_name}__isnull": False})
                            .values("id")
                            .distinct()
                            .count()
                        )

                    final_result[field_name] = count
                except Exception as e:
                    LOGGER.error(f"Error counting field {field_name}: {e}")
                    final_result[field_name] = 0

        # STEP 3: Count custom properties from Sample2Property table
        # Query separately for each property using JOIN optimization

        property_to_datatype = dict(
            models.Property.objects.values_list("name", "datatype")
        )
        property_names = PropertyViewSet.get_custom_property_names()

        for property_name in property_names:
            datatype = property_to_datatype.get(property_name)
            if not datatype:
                LOGGER.warning(f"Property {property_name} not found")
                continue

            try:
                # Django JOIN optimization: Sample -> Sample2Property -> Property
                # Uses index on property__name and datatype column
                count = (
                    queryset.filter(
                        properties__property__name=property_name,
                        **{f"properties__{datatype}__isnull": False},
                    )
                    .values("id")
                    .distinct()
                    .count()
                )

                final_result[property_name] = count
            except Exception as e:
                LOGGER.error(
                    f"Error counting property {property_name} (datatype: {datatype}): {e}"
                )
                final_result[property_name] = 0

        # STEP 4: Count mutation profiles (genomic and proteomic)
        # These queries are already optimized - keep as is
        try:
            # Count samples with nucleotide mutations
            genomic_count = (
                queryset.filter(
                    sequences__alignments__nucleotide_mutations__isnull=False
                )
                .values("id")
                .distinct()
                .count()
            )
            final_result["genomic_profiles"] = genomic_count
        except Exception as e:
            LOGGER.error(f"Error counting genomic profiles: {e}")
            final_result["genomic_profiles"] = 0

        try:
            # Count samples with amino acid mutations
            proteomic_count = (
                queryset.filter(
                    sequences__alignments__amino_acid_mutations__isnull=False
                )
                .values("id")
                .distinct()
                .count()
            )
            final_result["proteomic_profiles"] = proteomic_count
        except Exception as e:
            LOGGER.error(f"Error counting proteomic profiles: {e}")
            final_result["proteomic_profiles"] = 0

        # STEP 5: Cache result for xx minutes and return
        cache.set(cache_key, final_result, CACHE_OBJECT_TTL)

        return final_result

    def _get_samples_per_week(self, queryset):
        """
        Return a dict mapping calendar week to count, for each week between
        the earliest and latest collection_date.
        Weeks with zero records will be present with value 0.
        """
        weekly_qs = (
            queryset.annotate(week=TruncWeek("collection_date"))
            .values("week")
            .annotate(count=Count("id", distinct=True))
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
        # Generate cache key
        queryset_sql = str(queryset.query)
        cache_key = f"grouped_lineages_per_week:{hashlib.md5(queryset_sql.encode()).hexdigest()}"

        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

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

        # Cache for xx minutes
        cache.set(cache_key, result, 60)

        return result

    def _get_custom_property_plot(self, queryset, sample_property):
        # Determine if x_property and y_property are flexible or fixed
        flexible_properties = PropertyViewSet.get_custom_property_names()
        is_flexible = sample_property in flexible_properties
        if sample_property == "":
            result_dict = {}
        # custom properties
        elif is_flexible:
            datatype = (
                models.Property.objects.filter(name=sample_property)
                .values_list("datatype", flat=True)
                .first()
            )
            queryset = queryset.filter(properties__property__name=sample_property)
            # the value_char holds the sequencing reason values
            grouped_queryset = (
                queryset.values(f"properties__{datatype}")
                .annotate(total=Count("id", distinct=True))
                .order_by("properties__value_varchar")
            )
            result_dict = {
                item[f"properties__{datatype}"]: item["total"]
                for item in grouped_queryset
            }
        # fixed sample table prperty
        else:
            grouped_queryset = (
                queryset.values(sample_property)
                .annotate(total=Count("id", distinct=True))
                .order_by(sample_property)
            )
            result_dict = {
                str(item[sample_property]): item["total"] for item in grouped_queryset
            }  # str required for properties in date format

        return result_dict

    @action(detail=False, methods=["get"])
    def plot_samples_per_week(self, request: Request, *args, **kwargs):
        queryset = self.get_filtered_queryset(request).filter(
            collection_date__isnull=False
        )

        if not queryset.exists():
            return Response(data=[])
        else:
            samples_per_week = self._get_samples_per_week(queryset)
            return Response(data=list(samples_per_week.items()))

    @action(detail=False, methods=["get"])
    def plot_grouped_lineages_per_week(self, request: Request, *args, **kwargs):
        queryset = self.get_filtered_queryset(request).filter(
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
        queryset = self.get_filtered_queryset(request)
        result_dict = {}
        result_dict["metadata_coverage"] = self.get_metadata_coverage(queryset)
        return Response(data=result_dict)

    @action(detail=False, methods=["get"])
    def plot_custom(self, request: Request, *args, **kwargs):
        queryset = self.get_filtered_queryset(request)
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
        queryset = self.get_filtered_queryset(request)
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
                    .annotate(total=Count("id", distinct=True))
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
                    .annotate(total=Count("id", distinct=True))
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
                    .annotate(total=Count("id", distinct=True))
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
                    .annotate(total=Count("id", distinct=True))
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
