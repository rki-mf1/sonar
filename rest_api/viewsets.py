import csv
import json
import pathlib
import traceback
from dataclasses import dataclass
from datetime import datetime
from django.http import HttpResponse

import pandas as pd
from django.core.exceptions import FieldDoesNotExist
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from django.db.models import Count, F, Q, QuerySet, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from rest_api.data_entry.gbk_import import import_gbk_file

from . import models
from .serializers import (
    MutationSerializer,
    RepliconSerializer,
    Sample2PropertyBulkCreateOrUpdateSerializer,
    SampleGenomesSerializer,
    SampleSerializer,
)


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


@dataclass
class PropertyColumnMapping:
    db_property_name: str
    data_type: str


class RepliconViewSet(viewsets.ModelViewSet):
    queryset = models.Replicon.objects.all()
    serializer_class = RepliconSerializer

    @action(detail=False, methods=["get"])
    def distinct_genes(self, request: Request, *args, **kwargs):
        queryset = models.Replicon.objects.distinct("symbol").values("symbol")
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(molecule__reference__accession=ref)
        return Response({"genes": [item["symbol"] for item in queryset]})


class GeneViewSet(viewsets.ModelViewSet):
    queryset = models.Gene.objects.all()

    @action(detail=False, methods=["get"])
    def distinct_gene_symbols(self, request: Request, *args, **kwargs):
        queryset = models.Gene.objects.distinct("gene_symbol").values("gene_symbol")
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(molecule__reference__accession=ref)
        return Response({"gene_symbols": [item["gene_symbol"] for item in queryset]})


class MutationViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    queryset = models.Mutation.objects.all()
    serializer_class = MutationSerializer


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Property
        fields = "__all__"
        filter_backends = [DjangoFilterBackend]


class SampleViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    queryset = models.Sample.objects.all().order_by("id")
    serializer_class = SampleSerializer
    filter_backends = [DjangoFilterBackend]

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

    @action(detail=False, methods=["get"])
    def genomes(self, request: Request, *args, **kwargs):
        try:
            queryset = models.Sample.objects.all()
            if filter_params := request.query_params.get("filters"):
                filters = json.loads(filter_params)
                queryset = self.resolve_genome_filter(filters)
            profiles_qs = models.Mutation.objects.filter(
                ~Q(alt="N"), type="nt"
            ).only("ref", "alt", "start")
            proteomic_profiles_qs = models.Mutation.objects.filter(
                ~Q(alt="X"), type="cds"
            ).only("ref", "alt", "start")
            queryset = queryset.select_related("sequence").prefetch_related(
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
            )
            queryset = queryset.prefetch_related(
                "properties__property",
            )
            queryset = self.paginate_queryset(queryset)
            serializer = SampleGenomesSerializer(queryset, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as e:
            print(e)
            traceback.print_exc()
            raise e

    def resolve_genome_filter(self, filters) -> QuerySet:
        queryset = models.Sample.objects.all()
        filter_label_to_methods = {
            "Property": self.filter_property,
            "SNP Nt": self.filter_snp_profile_nt,
            "SNP AA": self.filter_snp_profile_aa,
            "Del Nt": self.filter_del_profile_nt,
            "Del AA": self.filter_del_profile_aa,
            "Ins Nt": self.filter_ins_profile_nt,
            "Ins AA": self.filter_ins_profile_aa,
        }
        for filter in filters.get("andFilter", []):
            method = filter_label_to_methods.get(filter.get("label"))
            if method:
                queryset = method(qs=queryset, **filter)
            else:
                raise Exception(f"filter_method not found for:{filter.get('label')}")
        or_query = Q()
        if len(filters.get("andFilter", [])) > 0:
            or_query |= Q(id__in=queryset)
        for or_filter in filters.get("orFilter", []):
            or_query |= Q(id__in=self.resolve_genome_filter(or_filter))
        return models.Sample.objects.filter(or_query)

    # WIP - not working yet
    @action(detail=False, methods=["get"])
    def download_genomes_export(self, request: Request, *args, **kwargs):
        queryset = models.Sample.objects.all()
        if filter_params := request.query_params.get("filters"):
            filters = json.loads(filter_params)
            queryset = self.resolve_genome_filter(filters)
        response = HttpResponse(content=queryset, content_type="text/csv")

    def filter_property(
        self,
        property_name,
        filter_type,
        value,
        exclude: bool = False,
        qs: QuerySet | None = None,
        *args,
        **kwargs,
    ):
        if qs is None:
            qs = models.Sample.objects.all()
            qs.prefetch_related("properties__property")
        if property_name in [field.name for field in models.Sample._meta.get_fields()]:
            query = {}
            query[f"{property_name}__{filter_type}"] = value
        else:
            datatype = models.Property.objects.get(name=property_name).datatype
            query = {f"properties__property__name": property_name}
            query[f"properties__{datatype}__{filter_type}"] = value
        qs = qs.exclude(**query) if exclude else qs.filter(**query)
        return qs

    def filter_snp_profile_nt(
        self,
        gene_symbol: str,
        ref_nuc: str,
        ref_pos: int,
        alt_nuc: str,
        qs: QuerySet | None = None,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> QuerySet:
        # For NT: ref_nuc followed by ref_pos followed by alt_nuc (e.g. T28175C).
        if qs is None:
            qs = models.Sample.objects.all()
        alignment_qs = models.Alignment.objects.filter(
            mutations__end=ref_pos,
            mutations__ref=ref_nuc,
            mutations__alt=alt_nuc,
            mutations__gene__gene_symbol=gene_symbol,
            mutations__type="nt",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        qs = qs.exclude(**filters) if exclude else qs.filter(**filters)
        return qs

    def filter_snp_profile_aa(
        self,
        protein_symbol: str,
        ref_aa: str,
        ref_pos: str,
        alt_aa: str,
        qs: QuerySet | None = None,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> QuerySet:
        # For AA: protein_symbol:ref_aa followed by ref_pos followed by alt_aa (e.g. OPG098:E162K)
        if qs is None:
            qs = models.Sample.objects.all()
        alignment_qs = models.Alignment.objects.filter(
            mutations__start=ref_pos,
            mutations__ref=ref_aa,
            mutations__alt=alt_aa,
            mutations__gene__gene_symbol=protein_symbol,
            mutations__type="cds",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        qs = qs.exclude(**filters) if exclude else qs.filter(**filters)
        return qs

    def filter_del_profile_nt(
        self,
        first_deleted_nt: str,
        last_deleted_nt: str,
        gene_symbol: str,
        qs: QuerySet | None = None,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> QuerySet:
        # For NT: del:first_NT_deleted-last_NT_deleted (e.g. del:133177-133186).
        if qs is None:
            qs = models.Sample.objects.all()
        alignment_qs = models.Alignment.objects.filter(
            mutations__gene__gene_symbol=gene_symbol,
            mutations__start=int(first_deleted_nt) - 1,
            mutations__end=last_deleted_nt,
            mutations__alt__in=[" ", "", None],
            mutations__type="nt",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        qs = qs.exclude(**filters) if exclude else qs.filter(**filters)
        return qs

    def filter_del_profile_aa(
        self,
        protein_symbol: str,
        first_deleted_aa: int,
        last_deleted_aa: int,
        exclude: bool = False,
        qs: QuerySet | None = None,
        *args,
        **kwargs,
    ) -> QuerySet:
        # For AA: protein_symbol:del:first_AA_deleted-last_AA_deleted (e.g. OPG197:del:34-35)
        if qs is None:
            qs = models.Sample.objects.all()
        alignment_qs = models.Alignment.objects.filter(
            mutations__gene__gene_symbol=protein_symbol,
            mutations__start=int(first_deleted_aa) - 1,
            mutations__end=last_deleted_aa,
            mutations__alt__in=[" ", "", None],
            mutations__type="cds",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        qs = qs.exclude(**filters) if exclude else qs.filter(**filters)
        return qs

    def filter_ins_profile_nt(
        self,
        gene_symbol: str,
        ref_nuc: str,
        ref_pos: int,
        alt_nucs: str,
        qs: QuerySet | None = None,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> QuerySet:
        # For NT: ref_nuc followed by ref_pos followed by alt_nucs (e.g. T133102TTT)
        if qs is None:
            qs = models.Sample.objects.all()
        alignment_qs = models.Alignment.objects.filter(
            mutations__end=ref_pos,
            mutations__ref=ref_nuc,
            mutations__alt=alt_nucs,
            mutations__gene__gene_symbol=gene_symbol,
            mutations__type="nt",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        qs = qs.exclude(**filters) if exclude else qs.filter(**filters)
        return qs

    def filter_ins_profile_aa(
        self,
        protein_symbol: str,
        ref_aa: str,
        ref_pos: int,
        alt_aas: str,
        qs: QuerySet | None = None,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> QuerySet:
        # For AA: protein_symbol:ref_aa followed by ref_pos followed by alt_aas (e.g. OPG197:A34AK)
        if qs is None:
            qs = models.Sample.objects.all()
        alignment_qs = models.Alignment.objects.filter(
            mutations__end=ref_pos,
            mutations__ref=ref_aa,
            mutations__alt=alt_aas,
            mutations__gene__gene_symbol=protein_symbol,
            mutations__type="cds",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        qs = qs.exclude(**filters) if exclude else qs.filter(**filters)
        return qs

    def _convert_date(self, date: str):
        datetime_obj = datetime.strptime(date, "%Y-%m-%d %H:%M:%S %z")
        return datetime_obj.date()

    @action(detail=False, methods=["post"])
    def import_properties_tsv(self, request: Request, *args, **kwargs):
        print("Importing properties...")
        sample_id_column = request.data.get("sample_id_column")
        column_mapping = self._convert_property_column_mapping(
            json.loads(request.data.get("column_mapping"))
        )
        if not sample_id_column or not column_mapping:
            return Response(
                "No sample_id_column or column_mapping provided.", status=400
            )
        if not request.FILES or "properties_tsv" not in request.FILES:
            return Response("No file uploaded.", status=400)
        tsv_file = request.FILES.get("properties_tsv")
        properties_df = pd.read_csv(
            self._temp_save_file(tsv_file), sep="\t", dtype=object
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
            models.Sample.objects.bulk_update(sample_updates, sample_property_names)
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
        return Response(
            {
                "sample_updates": len(sample_updates),
                "property_updates": len(property_updates),
            },
            status=200,
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
                    property["property"] = self.property_cache[
                        name
                    ] = models.Property.objects.get_or_create(
                        name=name, datatype=value["datatype"]
                    )[
                        0
                    ].id
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


class ReferenceSerializer(serializers.HyperlinkedModelSerializer):
    sequence = serializers.CharField(source="molecules.elements.sequence")

    class Meta:
        model = models.Reference
        fields = ["accession", "description", "organism", "standard", "sequence"]


class ReferenceViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    queryset = models.Reference.objects.all()
    serializer_class = ReferenceSerializer

    @action(detail=False, methods=["post"])
    def import_gbk(self, request: Request, *args, **kwargs):
        if not request.FILES or "gbk_file" not in request.FILES:
            return Response("No file uploaded.")
        gbk_file = request.FILES.get("gbk_file")
        import_gbk_file(gbk_file)
        return Response("OK")


class SNP1Serializer(serializers.HyperlinkedModelSerializer):
    reference_accession = serializers.CharField(
        source="element.molecule.reference.accession"
    )

    class Meta:
        model = models.Mutation
        fields = [
            "reference_accession",
            "ref",
            "alt",
            "start",
            "end",
        ]


class SNP1ViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    queryset = models.Mutation.objects.filter(
        ref__in=["C", "T", "G", "A"], alt__in=["C", "T", "G", "A"]
    ).exclude(ref=F("alt"))
    serializer_class = SNP1Serializer


class MutationSignatureSerializer(serializers.HyperlinkedModelSerializer):
    reference_accession = serializers.CharField(
        source="element.molecule.reference.accession"
    )
    count = serializers.IntegerField()

    class Meta:
        model = models.Mutation
        fields = [
            "reference_accession",
            "ref",
            "alt",
            "start",
            "end",
            "count",
        ]


class MutationSignatureRawSerializer(serializers.HyperlinkedModelSerializer):
    reference_accession = serializers.ReadOnlyField(
        source="element.molecule.reference.accession"
    )

    class Meta:
        model = models.Mutation
        fields = [
            "reference_accession",
            "ref",
            "alt",
            "start",
            "end",
        ]


class MutationSignatureViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    queryset = (
        models.Mutation.objects.filter(ref__in=["C", "T"], alt__in=["C", "T", "G", "A"])
        .exclude(ref=F("alt"))
        .annotate(count=Count("alignments__sequence__samples"))
    )
    serializer_class = MutationSignatureSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["element__molecule__reference__accession", "ref", "alt"]

    @action(detail=False, methods=["get"])
    def raw(self, request: Request, *args, **kwargs):
        queryset = models.Mutation.objects.filter(
            ref__in=["C", "T"], alt__in=["C", "T", "G", "A"]
        ).exclude(ref=F("alt"))
        page = self.paginate_queryset(queryset)
        serializer = MutationSignatureRawSerializer(page, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return self.get_paginated_response(serializer.data)


class PropertyViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    queryset = models.Sample2Property.objects.all()
    serializer_class = PropertySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["sample__id", "property__name"]

    @action(detail=False, methods=["get"])
    def distinct_properties(self, request: Request, *args, **kwargs):
        if not (property_name := request.query_params.get("property_name")):
            return Response("No property_name provided.")
        sample_property_fields = [
            field.name for field in models.Sample._meta.get_fields()
        ]
        print(property_name in sample_property_fields)
        if property_name in sample_property_fields:
            queryset = models.Sample.objects.all()
            queryset = queryset.distinct(property_name)
            return Response(
                {"values": [getattr(item, property_name) for item in queryset]}
            )
        queryset = models.Sample2Property.objects.filter(property__name=property_name)
        datatype = queryset[0].property.datatype
        queryset = queryset.distinct(datatype)
        return Response({"values": [getattr(item, datatype) for item in queryset]})

    @action(detail=False, methods=["get"])
    def unique_collection_dates(self, request: Request, *args, **kwargs):
        queryset = models.Sample2Property.objects.filter(
            property__name="COLLECTION_DATE", value_date__isnull=False
        ).distinct("value_date")
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(
                sample__sequence__alignment__element__molecule__reference__accession=ref
            )
        queryset = queryset.distinct("value_text")
        date_list = [item.value_date for item in queryset]
        return Response(data={"collection_dates": date_list})

    @action(detail=False, methods=["get"])
    def unique_countries(self, request: Request, *args, **kwargs):
        queryset = models.Sample2Property.objects.filter(
            property__name="COUNTRY", value_text__isnull=False
        )
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(
                sample__sequence__alignment__element__molecule__reference__accession=ref
            )
        queryset = queryset.distinct("value_text")
        country_list = [item.value_text for item in queryset]
        return Response(data={"countries": country_list})

    @action(detail=False, methods=["get"])
    def unique_sequencing_techs(self, request: Request, *args, **kwargs):
        queryset = models.Sample2Property.objects.filter(
            property__name="SEQ_TECH", value_text__isnull=False
        )
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(
                sample__sequence__alignment__element__molecule__reference__accession=ref
            )
        queryset = queryset.distinct("value_text")
        sequencing_tech_list = [item.value_text for item in queryset]
        return Response(data={"sequencing_techs": sequencing_tech_list})

    @action(detail=False, methods=["get"])
    def distinct_property_names(self, request: Request, *args, **kwargs):
        queryset = models.Property.objects.all()
        queryset = queryset.distinct("name")
        property_names = [item.name for item in queryset]
        sample_properties = models.Sample._meta.get_fields()
        property_names += [item.name for item in sample_properties]
        return Response(data={"property_names": property_names})


class MutationFrequencySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Mutation
        fields = [
            "element_symbol",
            "mutation_label",
            "count",
        ]


class AAMutationViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
):
    # input sequencing_tech list, country list, gene list, include partial bool,
    # reference_value int, min_nb_freq int = 1?
    queryset = models.Replicon.objects.all()

    @action(detail=False, methods=["get"])
    def mutation_frequency(self, request: Request, *args, **kwargs):
        country_list = request.query_params.getlist("countries")
        sequencing_tech_list = request.query_params.getlist("seq_techs")
        gene_list = request.query_params.getlist("genes")
        include_partial = bool(request.query_params.get("include_partial"))
        reference_value = request.query_params.get("reference_value")
        min_nb_freq = request.query_params.get("min_nb_freq")

        samples_query = models.Sample.objects.filter(
            sample2property__property__name="COUNTRY",
            sample2property__value_text__in=country_list,
        ).filter(
            sample2property__property__name="SEQ_TECH",
            sample2property__value_text__in=sequencing_tech_list,
        )
        if not include_partial:
            samples_query.filter(
                sample2property__property__name="GENOME_COMPLETENESS",
                sample2property__value_text="complete",
            )
        mutation_query = (
            models.Mutation.objects.filter(
                element__molecule__reference__accession=reference_value
            )
            .filter(alignments__sequence__samples__in=samples_query)
            .filter(element__symbol__in=gene_list)
            .annotate(mutation_count=Count("alignments__sequence__samples"))
            .filter(mutation_count__gte=min_nb_freq)
            .order_by("-mutation_count")
        )
        response = [
            {
                "symbol": mutation.element.symbol,
                "mutation": mutation.label,
                "count": mutation.mutation_count,
            }
            for mutation in mutation_query
        ]

        return Response(data=response)


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
