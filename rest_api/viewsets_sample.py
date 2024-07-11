import ast
import csv
import json
import pathlib
import traceback
from datetime import datetime

import pandas as pd
from dateutil.rrule import WEEKLY, rrule
from django.core.exceptions import FieldDoesNotExist
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import connection, transaction
from django.db.models import (
    CharField,
    Count,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    TextField,
)
from django.http import StreamingHttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response

from covsonar_backend.settings import DEBUG
from rest_api.data_entry.sample_job import delete_sample
from rest_api.serializers import SampleSerializer
from rest_api.utils import Response, resolve_ambiguous_NT_AA, strtobool
from rest_api.viewsets import PropertyColumnMapping, PropertyViewSet

from . import models
from .serializers import (
    Sample2PropertyBulkCreateOrUpdateSerializer,
    SampleGenomesSerializer,
    SampleGenomesSerializerVCF,
    SampleSerializer,
)


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
            "Sublineages": self.filter_sublineages,
        }

    @action(detail=False, methods=["get"])
    def statistics(self, request: Request, *args, **kwargs):
        response_dict = {}
        response_dict["distinct_mutations_count"] = (
            models.Mutation.objects.values("ref", "alt", "start", "end")
            .distinct()
            .count()
        )
        response_dict["samples_total"] = models.Sample.objects.all().count()
        response_dict["newest_sample_date"] = (
            models.Sample.objects.all()
            .order_by("-collection_date")
            .first()
            .collection_date
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
            queryset = models.Sample.objects.filter(self.resolve_genome_filter(filters))
        return queryset

    @action(detail=False, methods=["get"])
    def genomes(self, request: Request, *args, **kwargs):
        """

        TODO:
        1. Optimize the query (reduce the database hit)
        2. add accession of reference at the output
        3. add annotation info at the output
        """

        # we try to use bool(), but it is not working as expected.
        showNX = strtobool(request.query_params.get("showNX", "False"))
        vcf_format = strtobool(request.query_params.get("vcf_format", "False"))
        csv_stream = strtobool(request.query_params.get("csv_stream", "False"))
        self.has_property_filter = False
        queryset = self._get_filtered_queryset(request)
        if name_filter := request.query_params.get("name"):
            queryset = queryset.filter(name=name_filter)
        genomic_profiles_qs = (
            models.Mutation.objects.filter(type="nt").only(
                "ref", "alt", "start", "end", "gene"
            )
        ).prefetch_related("gene")
        proteomic_profiles_qs = (
            models.Mutation.objects.filter(type="cds").only(
                "ref", "alt", "start", "end", "gene"
            )
        ).prefetch_related("gene")
        annotation_qs = models.Mutation2Annotation.objects.prefetch_related(
            "mutation", "annotation"
        )
        if not showNX:
            genomic_profiles_qs = genomic_profiles_qs.filter(~Q(alt="N"))
            proteomic_profiles_qs = proteomic_profiles_qs.filter(~Q(alt="X"))
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

        # TODO: output in  VCF
        # if VCF
        # for obj in queryset.all():
        #    print(obj.name)
        #    for alignment in obj.sequence.alignments.all():
        #        print(alignment)
        # output only count
        if csv_stream:
            # TODO write output format
            echo_buffer = Echo()
            csv_writer = csv.writer(echo_buffer)
            rows = (
                csv_writer.writerow(row)
                for row in queryset.values_list(
                    "name",
                    "sequence__seqhash",
                )
            )
            response = StreamingHttpResponse(rows, content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="export.csv"'
            return response
        if vcf_format:
            queryset = self.paginate_queryset(queryset)
            serializer = SampleGenomesSerializerVCF(queryset, many=True)
            return self.get_paginated_response(serializer.data)
        if ordering := request.query_params.get("ordering"):
            property_names = PropertyViewSet.get_custom_property_names()
            ordering_col_name = ordering
            if ordering.startswith("-"):
                ordering_col_name = ordering[1:]
            if ordering_col_name in property_names:
                datatype = models.Property.objects.get(name=ordering_col_name).datatype
                queryset = queryset.order_by(
                    Subquery(
                        models.Sample2Property.objects.prefetch_related(
                            "property", "sample"
                        )
                        .filter(property__name=ordering_col_name)
                        .filter(sample=OuterRef("id"))
                        .values(datatype)
                    )
                )
                if ordering.startswith("-"):
                    queryset = queryset.reverse()
            else:
                queryset = queryset.order_by(ordering)
        queryset = self.paginate_queryset(queryset)
        serializer = SampleGenomesSerializer(queryset, many=True)
        return self.get_paginated_response(serializer.data)

    def _get_meta_data_coverage(self, queryset):
        dict = {}
        queryset = queryset.prefetch_related("properties__property")
        queryset = queryset.annotate(
            genomic_profiles_count=Count(
                "sequence__alignments__mutations",
                filter=Q(sequence__alignments__mutations__type="nt"),
            ),
            proteomic_profiles_count=Count(
                "sequence__alignments__mutations",
                filter=Q(sequence__alignments__mutations__type="cds"),
            ),
        )

        dict["genomic_profiles"] = queryset.filter(genomic_profiles_count__gt=0).count()
        dict["proteomic_profiles"] = queryset.filter(
            proteomic_profiles_count__gt=0
        ).count()

        property_names = PropertyViewSet.get_distinct_property_names()

        for field in models.Sample._meta.get_fields():
            field_name = field.name

            if field_name not in property_names:
                continue

            property_names.pop(property_names.index(field_name))

            if isinstance(field, (CharField, TextField)):
                non_empty_count = (
                    queryset.exclude(**{field_name: ""})
                    .exclude(**{field_name: None})
                    .count()
                )
            else:
                non_empty_count = queryset.exclude(**{field_name: None}).count()
            dict[field_name] = non_empty_count

        for property_name in property_names:
            datatype = models.Property.objects.get(name=property_name).datatype
            dict[property_name] = (
                queryset.exclude(
                    **{
                        "properties__property__name": property_name,
                        f"properties__{datatype}": "",
                    }
                )
                .exclude(
                    **{
                        "properties__property__name": property_name,
                        f"properties__{datatype}": None,
                    }
                )
                .count()
            )

        return dict

    def _get_samples_per_week(self, queryset):
        dict = {}
        queryset = (
            queryset.extra(
                select={
                    "week": "EXTRACT('week' FROM collection_date)",
                    "year": "EXTRACT('year' FROM collection_date)",
                }
            )
            .values("year", "week")
            .annotate(count=Count("id"), collection_date=Min("collection_date"))
            .order_by("year", "week")
        )

        start_date = queryset.first()["collection_date"]
        end_date = queryset.last()["collection_date"]

        for dt in rrule(
            WEEKLY, dtstart=start_date, until=end_date
        ):  # generate all weeks between start and end dates and assign default value 0
            dict[f"{dt.year}-W{dt.isocalendar()[1]:02}"] = 0

        for item in queryset:  # fill in count values of present weeks
            dict[f"{item['year']}-W{int(item['week']):02}"] = item["count"]

        return dict

    @action(detail=False, methods=["get"])
    def filtered_statistics(self, request: Request, *args, **kwargs):
        queryset = self._get_filtered_queryset(request)
        dict = {}

        dict["filtered_total_count"] = queryset.count()
        dict["meta_data_coverage"] = self._get_meta_data_coverage(queryset)
        dict["samples_per_week"] = self._get_samples_per_week(queryset)

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
        print(q_obj)
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

        self.has_property_filter = True
        if property_name in [field.name for field in models.Sample._meta.get_fields()]:
            query = {}
            query[f"{property_name}__{filter_type}"] = value
            print(query)
        else:
            datatype = models.Property.objects.get(name=property_name).datatype
            print(datatype)
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
        first_deleted: int,
        last_deleted: int,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> Q:
        # For AA: protein_symbol:del:first_AA_deleted-last_AA_deleted (e.g. OPG197:del:34-35)

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
        lineage,
        exclude: bool = False,
        *args,
        **kwargs,
    ):
        split = lineage.split(".")
        alias = None
        if models.LineageAlias.objects.filter(alias=split[0]).exists():
            alias = split.pop(0)
            lineage = ".".join(split)
        lineage = models.Lineage.objects.get(lineage=lineage, prefixed_alias=alias)
        sublineages = (
            str(lineage)
            for lineage in lineage.get_sublineages(include_recombinants=False)
        )
        return self.filter_property("lineage", "in", sublineages, exclude)

    def _convert_date(self, date: str):
        datetime_obj = datetime.strptime(date, "%Y-%m-%d %H:%M:%S %z")
        return datetime_obj.date()

    @action(detail=False, methods=["post"])
    def import_properties_tsv(self, request: Request, *args, **kwargs):
        print("Importing properties...")
        timer = datetime.now()
        sample_id_column = request.data.get("sample_id_column")

        column_mapping = self._convert_property_column_mapping(
            json.loads(request.data.get("column_mapping"))
        )
        if not sample_id_column:
            return Response(
                {"detail": "No sample_id_column is provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not column_mapping:
            return Response(
                {"detail": "No column_mapping is provided, nothing to import."},
                status=status.HTTP_200_OK,
            )

        if not request.FILES or "properties_tsv" not in request.FILES:
            return Response("No file uploaded.", status=400)
        # TODO: what if it is csv?
        tsv_file = request.FILES.get("properties_tsv")

        properties_df = pd.read_csv(
            self._temp_save_file(tsv_file),
            sep="\t",
            dtype=object,
            keep_default_na=False,
        )
        if sample_id_column not in properties_df.columns:
            return Response(
                {
                    "detail": f"Incorrect mapping column: '{sample_id_column}', please check property file."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        sample_property_names = []
        custom_property_names = []
        for property_name in properties_df.columns:
            if property_name in column_mapping.keys():
                db_property_name = column_mapping[property_name].db_property_name
                try:
                    models.Sample._meta.get_field(db_property_name)
                    sample_property_names.append(db_property_name)
                except FieldDoesNotExist:
                    custom_property_names.append(property_name)

        sample_id_set = set(properties_df[sample_id_column])
        samples = models.Sample.objects.filter(name__in=sample_id_set).iterator()
        sample_updates = []
        property_updates = []
        print("Updating samples...")
        properties_df.convert_dtypes()
        properties_df.set_index(sample_id_column, inplace=True)
        for sample in samples:
            row = properties_df[properties_df.index == sample.name]

            for name, value in row.items():
                if name in column_mapping.keys():
                    db_name = column_mapping[name].db_property_name
                    if db_name in sample_property_names:
                        setattr(sample, db_name, value.values[0])
            sample_updates.append(sample)

            property_updates += self._create_property_updates(
                sample,
                {
                    column_mapping[name].db_property_name: {
                        "value": value.values[0],
                        "datatype": column_mapping[name].data_type,
                    }
                    for name, value in row.items()
                    if name in custom_property_names
                },
                True,
            )

        print("Saving...")
        with transaction.atomic():
            # update based prop. for Sample
            if (
                len(sample_property_names) > 0
            ):  # when there is no update/add to based prop.
                models.Sample.objects.bulk_update(sample_updates, sample_property_names)

            # update custom prop. for Sample
            serializer = Sample2PropertyBulkCreateOrUpdateSerializer(
                data=property_updates, many=True
            )
            serializer.is_valid(raise_exception=True)
            models.Sample2Property.objects.bulk_create(
                [models.Sample2Property(**data) for data in serializer.validated_data],
                update_conflicts=True,
                update_fields=[
                    "value_integer",
                    "value_float",
                    "value_text",
                    "value_varchar",
                    "value_blob",
                    "value_date",
                    "value_zip",
                ],
                unique_fields=["sample", "property"],
            )

        print("Done.")
        print(f"Import done in {datetime.now() - timer}")
        return Response(
            {"detail": "File uploaded successfully"}, status=status.HTTP_201_CREATED
        )

    def _convert_property_column_mapping(
        self, column_mapping: dict[str, str]
    ) -> dict[str, PropertyColumnMapping]:
        return {
            db_property_name: PropertyColumnMapping(**db_property_info)
            for db_property_name, db_property_info in column_mapping.items()
        }

    def _create_property_updates(
        self, sample, properties: dict, use_property_cache=False
    ) -> list[dict]:
        property_objects = []
        if use_property_cache and not hasattr(self, "property_cache"):
            self.property_cache = {}
        for name, value in properties.items():
            property = {"sample": sample.id, value["datatype"]: value["value"]}
            if use_property_cache:
                if name in self.property_cache.keys():
                    property["property"] = self.property_cache[name]
                else:
                    property["property"] = self.property_cache[name] = (
                        models.Property.objects.get_or_create(
                            name=name, datatype=value["datatype"]
                        )[0].id
                    )
            else:
                property["property__name"] = name
            property_objects.append(property)
        return property_objects

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
        file_path = pathlib.Path("import_data") / uploaded_file.name
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
