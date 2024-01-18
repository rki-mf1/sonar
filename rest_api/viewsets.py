import csv
import json
import os
import pathlib
import pickle
import traceback
from dataclasses import dataclass
from datetime import datetime
import zipfile
from django.http import HttpResponse

import pandas as pd

from django.core.exceptions import FieldDoesNotExist
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from django.db.models import Count, F, Q, QuerySet, Prefetch
from covsonar_backend.settings import DEBUG, IMPORTED_DATA_DIR
from django_filters.rest_framework import DjangoFilterBackend
from rest_api.data_entry.reference_job import delete_reference
from rest_api.data_entry.sample_job import delete_sample
from rest_api.utils import create_error_response, create_success_response, resolve_ambiguous_NT_AA, strtobool, write_to_file
from rest_framework import generics, serializers, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework import status

from django.core.serializers import serialize

from rest_api.data_entry.gbk_import import import_gbk_file

from . import models
from .serializers import (
    AlignmentSerializer,
    GeneSerializer,
    ReferenceSerializer,
    MutationSerializer,
    RepliconSerializer,
    Sample2PropertyBulkCreateOrUpdateSerializer,
    SampleGenomesSerializer,
    SampleGenomesSerializerVCF,
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


class AlignmentViewSet(viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,):
    """
    AlignmentViewSet
    """
    queryset = models.Alignment.objects.all()
    serializer_class = AlignmentSerializer

    @action(detail=False, methods=["get"], url_path='get_alignment_data/(?P<seqhash>[a-zA-Z0-9]+)/(?P<replicon_id>[0-9]+)')
    def get_alignment_data(self, request: Request, seqhash=None, replicon_id=None):
        # if seq_id is None  or element_id is None:
        #    return create_error_response(message='Some parameters are missing in URL')
        # already taking care by Django
        sample_data = {}
        # replicon_id = element_id
        queryset =  self.queryset.filter(sequence__seqhash=seqhash , replicon_id= replicon_id )
        sample_data = queryset.values()
        if sample_data:
            sample_data = sample_data[0]
        return create_success_response(data=sample_data)


class RepliconViewSet(viewsets.ModelViewSet):
    queryset = models.Replicon.objects.all()
    serializer_class = RepliconSerializer

    @action(detail=False, methods=["get"])
    def distinct_genes(self, request: Request, *args, **kwargs):
        queryset = models.Replicon.objects.distinct("symbol").values("symbol")
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(molecule__reference__accession=ref)
        return Response({"genes": [item["symbol"] for item in queryset]})

    @action(detail=False, methods=["get"])
    def get_molecule_data(self, request: Request, *args, **kwargs):
        sample_data = {}

        if replicon_id := request.query_params.get("replicon_id"):
            queryset_obj = self.queryset.filter(id=replicon_id)
        elif ref := request.query_params.get("reference_accession"):
            queryset_obj = self.queryset.filter(reference__accession=ref)
        else:
            return create_error_response(message='Accession ID is missing')
        
        if queryset_obj.exists():
            # NOTE: Fixed value for translation ID
            # sample_data.translation_id = 1
            # sample_data = serialize('json', queryset_obj)
            sample_data = queryset_obj.values()
            for obj in sample_data:
                obj["translation_id"] = 1
        return create_success_response(data=sample_data)
    
    @action(detail=False, methods=["get"])
    def get_source_data(self, request: Request, *args, **kwargs):

        """
        Returns the source data given a molecule id.

        Args:
            molecule_id (int): The id of the molecule.

        Returns:
            Optional[str]: The source if it exists, None otherwise.

        """
        sample_data = {}

        if molecule_id := request.query_params.get("molecule_id"):
            queryset = self.queryset.filter(reference__accession=molecule_id)
            sample_data = queryset.values()
        else:
            return create_error_response(message='Accession ID is missing')
        return create_success_response(data=sample_data)

class GeneViewSet(viewsets.ModelViewSet):
    queryset = models.Gene.objects.all()
    serializer_class = GeneSerializer

    @action(detail=False, methods=["get"])
    def distinct_gene_symbols(self, request: Request, *args, **kwargs):
        queryset = models.Gene.objects.distinct("gene_symbol").values("gene_symbol")
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(molecule__reference__accession=ref)
        return Response({"gene_symbols": [item["gene_symbol"] for item in queryset]})

    @action(detail=False, methods=["get"])
    def get_gene_data(self, request: Request):
        sample_data = {}

        if ref_acc := request.query_params.get("ref_acc"):
            # queryset =  models.Gene.objects.filter(replicon__reference__accession=ref_acc)
            
            queryset = models.GeneSegment.objects.select_related("gene__replicon__reference").filter(gene__replicon__reference__accession=ref_acc)
        elif replicon_id := request.query_params.get("replicon_id"):
            queryset = self.queryset.filter(replicon_id=replicon_id)
        else:
            return create_error_response(message='Searchable field is missing')

        sample_data = []
        for item in queryset.all():
            _data = {}
            _data["reference.id"] = item.gene.replicon.reference.id
            _data["reference.accession"] = item.gene.replicon.reference.accession
            _data["reference.description"] = item.gene.replicon.reference.description
            _data["reference.organism"] = item.gene.replicon.reference.organism
            _data["reference.host"] = item.gene.replicon.reference.host
            _data["replicon.id"] = item.gene.replicon.id
            _data["replicon.accession"] = item.gene.replicon.accession
            _data["replicon.description"] = item.gene.replicon.description
            _data["replicon.length"] = item.gene.replicon.length
            _data["replicon.segment_number"] = item.gene.replicon.segment_number
            _data["gene.id"] = item.gene.id
            _data["gene.start"] = item.gene.start
            _data["gene.end"] = item.gene.end
            _data["gene.description"] = item.gene.description
            _data["gene.gene_symbol"] = item.gene.gene_symbol
            _data["gene.gene_accession"] = item.gene.gene_accession
            _data["gene.gene_sequence"] = item.gene.gene_sequence
            _data["gene.cds_sequence"] = item.gene.cds_sequence
            _data["gene.cds_accession"] = item.gene.cds_accession
            _data["gene.cds_symbol"] = item.gene.cds_symbol
            _data["gene_segment.id"] = item.id
            _data["gene_segment.gene_id"] = item.gene_id
            _data["gene_segment.start"] = item.start
            _data["gene_segment.end"] = item.end
            _data["gene_segment.strand"] = item.strand
            _data["gene_segment.base"] = item.base
            _data["gene_segment.segment"] = item.segment
            sample_data.append(_data)

        # sample_data =queryset.values()
        
        return create_success_response(data=sample_data)
    
class MutationViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    queryset = models.Mutation.objects.all()
    serializer_class = MutationSerializer

    @action(detail=False, methods=["get"])
    def distinct_alts(self, request: Request, *args, **kwargs):
        queryset = models.Mutation.objects.distinct("alt").values("alt")
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(element__replicon__reference__accession=ref)
        return Response({"alts": [item["alt"] for item in queryset]})


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
    lookup_field = "name"

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

            # we try to use bool(), but it is not working as expected.
                
            showNX  = strtobool(request.query_params.get("showNX"))
            vcf_format = strtobool(request.query_params.get("vcf_format"))

            if not showNX:
                genomic_profiles_qs = models.Mutation.objects.filter(
                    ~Q(alt="N"), type="nt"
                ).only("ref", "alt", "start","end").order_by("start")
                proteomic_profiles_qs = models.Mutation.objects.filter(
                    ~Q(alt="X"), type="cds"
                ).only("ref", "alt", "start","end").order_by("start")
            else:
                genomic_profiles_qs = models.Mutation.objects.filter(
                ).only("ref", "alt", "start","end").order_by("start")
                proteomic_profiles_qs = models.Mutation.objects.filter(
                ).only("ref", "alt", "start","end").order_by("start")

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

            # if VCF 
            # for obj in queryset.all():
            #    print(obj.name)
            #    for alignment in obj.sequence.alignments.all():
            #        print(alignment)
            if vcf_format:
                queryset = self.paginate_queryset(queryset)
                serializer = SampleGenomesSerializerVCF(queryset, many=True)
                return self.get_paginated_response(serializer.data)
            else:
                queryset = queryset.prefetch_related(
                    "properties__property",
                )

                queryset = self.paginate_queryset(queryset)
                serializer = SampleGenomesSerializer(queryset, many=True)
                return self.get_paginated_response(serializer.data)
        
        except Exception as e:
            print(e)
            traceback.print_exc()
            return create_error_response(message=str(e))

    def resolve_genome_filter(self, filters, level=0) -> QuerySet:
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
        print("andFilter: ---- lv:",level)
        for filter in filters.get("andFilter", []):
            print(filter)
            method = filter_label_to_methods.get(filter.get("label"))
            if method:
                queryset = method(qs=queryset, **filter)
            else:
                raise Exception(f"filter_method not found for:{filter.get('label')}")
            
        or_query = Q()
        if len(filters.get("andFilter", [])) > 0:
            or_query |= Q(id__in=queryset)

        print("orFilter: ---- lv:",level)
        for or_filter in filters.get("orFilter", []):
            or_query |= Q(id__in=self.resolve_genome_filter(or_filter, level=level+1))

        print("end: -------- lv:",level)
        final_queryset = models.Sample.objects.filter(or_query)

        if level == 0:
            print()
            print(final_queryset.query)
            print()
        return models.Sample.objects.filter(or_query)

    # WIP - not working yet
    @action(detail=False, methods=["get"])
    def download_genomes_export(self, request: Request, *args, **kwargs):
        queryset = models.Sample.objects.all()
        if filter_params := request.query_params.get("filters"):
            filters = json.loads(filter_params)
            queryset = self.resolve_genome_filter(filters)
        response = HttpResponse(content=queryset, content_type="text/csv")

    @action(detail=True, methods=["get"])
    def get_sample_data(self, request: Request, *args, **kwargs):
        sample = self.get_object()
        serializer = SampleGenomesSerializer(sample)
        return Response(serializer.data)

    def filter_property(
        self,
        property_name,
        filter_type,
        value,
        exclude: bool = False,
        qs: QuerySet | None = None,
        with_sublineage: bool = False,
        *args,
        **kwargs,
    ):
        if qs is None:
            qs = models.Sample.objects.all()
            qs.prefetch_related("properties__property")

        if filter_type =="contains":
            value = value.strip("%")

        if property_name in [field.name for field in models.Sample._meta.get_fields()]:

            query = {}

            # with sublineage search 
            # search A.2.5 also includes A.2.5.1,A.2.5.2,A.2.5.3
            # TODO: however if we combine A% (contains) with sublineage search??
            if with_sublineage:
                value_list = []
                # the parent lineage
                value_list.append(value)

                # NOTE: warning the lineage table can return "none",
                rows = models.Lineages.objects.filter(lineage=value).values('sublineage')
                if rows:
                    value_list.extend(rows[0]["sublineage"].split(','))


                query[f"{property_name}__in"] = value_list
            else:
                query[f"{property_name}__{filter_type}"] = value
            print(query)
        else:
            datatype = models.Property.objects.get(name=property_name).datatype
            query = {f"properties__property__name": property_name}
            query[f"properties__{datatype}__{filter_type}"] = value

        qs = qs.exclude(**query) if exclude else qs.filter(**query)
        return qs

    def filter_snp_profile_nt(
        self,
        # gene_symbol: str,
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
        # Create Q() objects for each condition
        if alt_nuc == "N":
            mutation_alt = Q() 
            for  x in resolve_ambiguous_NT_AA(type="nt", char = alt_nuc):
                mutation_alt  = mutation_alt | Q(mutations__alt=x)
            # Unsupported lookup 'alt_in' for ForeignKey or join on the field not permitted.
            # mutation_alt = Q(
            #     mutations__alt_in=resolve_ambiguous_NT_AA(type="nt", char = alt_nuc)
            # )
        else:
            if alt_nuc == "n":
                alt_nuc = "N"

            mutation_alt = Q(
                mutations__alt=alt_nuc
            )
        mutation_condition = (Q(mutations__end=ref_pos) &  Q(mutations__ref=ref_nuc) & (mutation_alt) & Q(mutations__type="nt") )
        if DEBUG:
            print(mutation_condition)

        alignment_qs = models.Alignment.objects.filter(mutation_condition)
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

        if alt_aa == "X":
            mutation_alt = Q() 
            for  x in resolve_ambiguous_NT_AA(type="aa", char = alt_aa):
                mutation_alt  = mutation_alt | Q(mutations__alt=x)
        else:
            if alt_aa == "x":
                alt_aa = "X"    
            mutation_alt = Q(
                mutations__alt=alt_aa
            )

        mutation_condition = (Q(mutations__end=ref_pos) &  Q(mutations__ref=ref_aa) & (mutation_alt) 
                              & Q(mutations__gene__gene_symbol=protein_symbol) & Q(mutations__type="cds") )

        alignment_qs = models.Alignment.objects.filter(mutation_condition)

        filters = {"sequence__alignments__in": alignment_qs}
        qs = qs.exclude(**filters) if exclude else qs.filter(**filters)
        return qs

    def filter_del_profile_nt(
        self,
        first_deleted: str,
        last_deleted: str,
        qs: QuerySet | None = None,
        exclude: bool = False,
        *args,
        **kwargs,
    ) -> QuerySet:
        """
        add new field exact match or not
        """
        # For NT: del:first_NT_deleted-last_NT_deleted (e.g. del:133177-133186).
        if qs is None:
            qs = models.Sample.objects.all()
        alignment_qs = models.Alignment.objects.filter(
            mutations__start=int(first_deleted) - 1,
            mutations__end=last_deleted,
            mutations__alt__in=[" ", "", None],
            mutations__type="nt",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        qs = qs.exclude(**filters) if exclude else qs.filter(**filters)
        return qs

    def filter_del_profile_aa(
        self,
        protein_symbol: str,
        first_deleted: int,
        last_deleted: int,
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
            mutations__start=int(first_deleted) - 1,
            mutations__end=last_deleted,
            mutations__alt__in=[" ", "", None],
            mutations__type="cds",
        )
        filters = {"sequence__alignments__in": alignment_qs}
        qs = qs.exclude(**filters) if exclude else qs.filter(**filters)
        return qs

    def filter_ins_profile_nt(
        self,
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
        # TODO: what if it is csv?
        tsv_file = request.FILES.get("properties_tsv")

        properties_df = pd.read_csv(
            self._temp_save_file(tsv_file), sep="\t", dtype=object, keep_default_na=False
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
        return create_success_response(message='File uploaded successfully',
                                    return_status=status.HTTP_201_CREATED)

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
    
    @action(detail=False, methods=["get"])
    def get_sample_data(self, request: Request, *args, **kwargs):      
        sample_name = request.GET.get("sample_data") 
        if not sample_name:
            return create_error_response(message='Sample name is missing')
        sample_model = models.Sample.objects.filter(name=sample_name).extra(select={'sample_id':'sample.id'}).values('sample_id',"name", 'sequence__seqhash')
        if sample_model:
            sample_data = list(sample_model)[0]
            if len(sample_model)>1:
                # Not sure ....---
                print("more than one sample was using same name.")
        else:
            print("Cannot find:", sample_name)
            sample_data = {}

        return create_success_response(data=sample_data)
    
    @action(detail=False, methods=["post"])
    def delete_sample_data(self, request: Request, *args, **kwargs):    
        sample_data = {}
        reference_accession = request.data.get("reference_accession", "")
        sample_list =  json.loads(request.data.get("sample_list"))
        if DEBUG:
            print("Reference Accession:", reference_accession)
            print("Sample List:", sample_list)

        sample_data = delete_sample( sample_list=sample_list)

        return create_success_response( data=sample_data)

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
            return create_error_response(message="No file uploaded.")
        
        if "translation_id" not in request.data:
            return create_error_response(message="No translation_id provided.")
        
        translation_id = int(request.data.get("translation_id"))
        gbk_file = request.FILES.get("gbk_file")

        import_gbk_file(gbk_file, translation_id)
        return create_success_response(message="OK")
    
    @action(detail=False, methods=["post"])
    def delete_reference(self, request: Request, *args, **kwargs):

        if "accession" not in request.data:
            return create_error_response(message="No accession provided.")
        
        accession = request.data.get("accession")

        data = delete_reference(accession)
        return create_success_response(message="OK", data=data)


    @action(detail=False, methods=["get"])
    def distinct_accessions(self, request: Request, *args, **kwargs):
        queryset =  models.Reference.objects.all()
        accession = ([item.accession for item in queryset])
        return create_success_response(data= accession)


    @action(detail=False, methods=["get"])
    def get_all_references(self, request: Request, *args, **kwargs):
        queryset =  models.Reference.objects.all()
        sample_data = queryset.values()
        return  create_success_response(data= sample_data)
    # multilple get in one.

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


    @action(detail=False, methods=["get"])
    def get_all_properties(self, request: Request, *args, **kwargs):
        """
        "value_integer",
        "value_float",
        "value_text",
        "value_varchar",
        "value_blob",
        "value_date",
        "value_zip",
        """
        # fixed datatype accroding to the Sample Table.
        data_list = [
            {"name": "collection_date", "query_type": "value_date", "description": "Collected date of sample"},
            {"name": "length", "query_type": "value_integer", "description": "Length of sequence"},
            {"name": "lab", "query_type": "value_varchar", "description": ""},
            {"name": "zip_code", "query_type": "value_varchar", "description": ""},
            {"name": "host", "query_type": "value_varchar", "description": "A host (e.g., Human)"},
            {"name": "genome_completeness", "query_type": "value_varchar", "description": "Genome completeness (partial/complete)"},
            {"name": "lineage", "query_type": "value_varchar", "description": ""},
            {"name": "sequencing_tech", "query_type": "value_varchar", "description": ""},
            {"name": "processing_date", "query_type": "value_date", "description": ""},
            {"name": "country", "query_type": "value_varchar", "description": ""},
        ]  # from SAMPLE TABLE
        cols = [
            "name",
            "query_type",
            "description",
        ]

        for _property_queryset in models.Property.objects.all():
            data_list.append({
                "name": _property_queryset.name,
                "query_type": _property_queryset.datatype,
                "description": _property_queryset.description
            })
        data ={
            "keys":cols,
            "values": data_list
        }
        return create_success_response(data=data)

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


class ResourceViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["get"])
    def get_translation_table(self, request: Request):
        # file path -> resource/1.tt

        file_path = os.path.join("resource", "1.tt")
        try:
            with open(file_path, "rb") as file:
                translation_table = pickle.load(file)
        except FileNotFoundError:
            return create_error_response(message="error: File not found", return_status=404)
        except Exception as e:
            return create_error_response({"error": str(e)}, return_status=500)
        
        return create_success_response(data=translation_table)
    
class FileUploadViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["post"])
    def import_upload(self, request, *args, **kwargs):
        """
        if "sample_file" not in request.FILES:
            return create_error_response(message="No sample file uploaded.", return_status=400)
        if "anno_file" not in request.FILES:
            return create_error_response(message="No ann file uploaded.", return_status=400)
        if "var_file" not in request.FILES:
            return create_error_response(message="No var file uploaded.", return_status=400)
        sample_file = request.FILES.get("sample_file")
        anno_file = request.FILES.get("anno_file")
        var_file = request.FILES.get("var_file")
        _save_path = pathlib.Path(IMPORTED_DATA_DIR, "samples", sample_file.name[0:2], sample_file.name)
        write_to_file(_save_path, sample_file)
        _save_path = pathlib.Path(IMPORTED_DATA_DIR, "anno", anno_file.name[0:2], anno_file.name)
        write_to_file(_save_path, anno_file)
        _save_path = pathlib.Path(IMPORTED_DATA_DIR, "var", var_file.name[0:2], var_file.name)
        write_to_file(_save_path, var_file)
        """

        if "zip_file" not in request.FILES:
            return create_error_response(message="No zip file uploaded.", return_status=400)

        zip_file = request.FILES.get("zip_file")
        # Extract files from the BytesIO
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(IMPORTED_DATA_DIR)
            # to view list of files and file details in ZIP
            # for file_info in zip_ref.infolist():
            #    print(file_info)

        return create_success_response(message='File uploaded successfully', return_status=status.HTTP_201_CREATED)




class FuctionsViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["get"])
    def match(self, request: Request):
        return create_success_response(return_status=status.HTTP_200_OK)