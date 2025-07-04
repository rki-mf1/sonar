from datetime import datetime
from datetime import timezone
from functools import reduce
import io
import json
import operator
import os
import pickle
import uuid
import zipfile

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Count
from django.db.models import F
from django.db.models import Q
from django.db.models import Sum
from django.db.utils import IntegrityError
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from covsonar_backend.settings import LOGGER
from covsonar_backend.settings import SONAR_DATA_ENTRY_FOLDER
from rest_api.data_entry.gbk_import import import_gbk_file
from rest_api.data_entry.property_job import delete_property
from rest_api.data_entry.property_job import find_or_create_property
from rest_api.data_entry.reference_job import delete_reference
from rest_api.data_entry.sample_entry_job import check_for_new_data
from rest_api.management.commands.import_lineage import LineageImport
from rest_api.utils import generate_job_ID
from rest_api.utils import get_distinct_gene_symbols
from rest_api.utils import parse_default_data
from rest_api.utils import PropertyColumnMapping
from rest_api.utils import strtobool
from . import models
from .serializers import AlignmentSerializer
from .serializers import AminoAcidMutationSerializer
from .serializers import GeneSerializer
from .serializers import ImportLogSerializer
from .serializers import LineagesSerializer
from .serializers import NucleotideMutationSerializer
from .serializers import ProcessingJobSerializer
from .serializers import PropertySerializer
from .serializers import ReferenceSerializer
from .serializers import RepliconSerializer


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


class AlignmentViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    """
    AlignmentViewSet
    """

    queryset = models.Alignment.objects.all()
    serializer_class = AlignmentSerializer

    @action(
        detail=False,
        methods=["get"],
        url_path="get_alignment_data/(?P<seqhash>[a-zA-Z0-9]+)/(?P<replicon_id>[0-9]+)",
    )
    def get_alignment_data(self, request: Request, seqhash=None, replicon_id=None):
        sample_data = {}
        queryset = self.queryset.filter(
            sequence__seqhash=seqhash, replicon_id=replicon_id
        )
        sample_data = queryset.values()
        if sample_data:
            sample_data = sample_data[0]
        return Response(sample_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def get_bulk_alignment_data(self, request: Request, *args, **kwargs):
        data = json.loads(request.body.decode("utf-8"))
        sample_data_list = data.get("sample_data", [])

        # Extract values from the list
        seqhash_values = [item.get("seqhash") for item in sample_data_list]
        replicon_id_values = [item.get("replicon_id") for item in sample_data_list]

        queryset = models.Alignment.objects.filter(
            reduce(
                operator.or_,
                (
                    Q(sequence__seqhash=seqhash, replicon_id=replicon_id)
                    for seqhash, replicon_id in zip(seqhash_values, replicon_id_values)
                ),
            )
        )
        queryset = queryset.select_related("sequence")

        # Convert the queryset to a list of dictionaries
        # sample_data = list(queryset.values())
        sample_data = list(
            queryset.extra(
                select={"alignement_id": "alignment.id", "sequence_id": "sequence.id"}
            ).values(
                "replicon_id",
                "alignement_id",
                "sequence_id",
                "sequence__sample__name",
            )
        )
        return Response(data=sample_data, status=status.HTTP_200_OK)


class RepliconViewSet(viewsets.ModelViewSet):
    queryset = models.Replicon.objects.all()
    serializer_class = RepliconSerializer

    @action(detail=False, methods=["get"])
    def distinct_genes(self, request: Request, *args, **kwargs):
        queryset = models.Replicon.objects.distinct("symbol").values("symbol")
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(molecule__reference__accession=ref)
        return Response(
            {"genes": [item["symbol"] for item in queryset]}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"])
    def distinct_accessions(self, request: Request, *args, **kwargs):
        queryset = models.Replicon.objects.only("accession").values_list(
            "accession", flat=True
        )
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(molecule__reference__accession=ref)
        distinct_accessions = queryset.distinct()

        return Response(
            {"accessions": distinct_accessions},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def get_molecule_data(self, request: Request, *args, **kwargs):
        sample_data = {}

        if replicon_id := request.query_params.get("replicon_id"):
            queryset_obj = self.queryset.filter(id=replicon_id)
        elif ref := request.query_params.get("reference_accession"):
            queryset_obj = self.queryset.filter(reference__accession=ref)
        else:
            return Response(
                {"detail": "Accession ID is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if queryset_obj.exists():
            # NOTE: Fixed value for translation ID
            # sample_data.translation_id = 1
            # sample_data = serialize('json', queryset_obj)
            sample_data = queryset_obj.values()
            for obj in sample_data:
                obj["translation_id"] = 1
        return Response(data=sample_data, status=status.HTTP_200_OK)

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
            return Response(
                {"detail": "Accession ID is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(data=sample_data, status=status.HTTP_200_OK)


class GeneViewSet(viewsets.ModelViewSet):
    queryset = models.Gene.objects.all()
    serializer_class = GeneSerializer

    @action(detail=False, methods=["get"])
    def distinct_gene_symbols(self, request: Request, *args, **kwargs):
        reference = request.query_params.get("reference")
        gene_symbols = get_distinct_gene_symbols(reference=reference)
        return Response(
            {"gene_symbols": gene_symbols},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def get_gene_data(self, request: Request):
        sample_data = {}

        if ref_acc := request.query_params.get("ref_acc"):
            # queryset =  models.Gene.objects.filter(replicon__reference__accession=ref_acc)
            queryset = models.GeneSegment.objects.select_related(
                "gene__replicon__reference"
            ).filter(gene__replicon__reference__accession=ref_acc)

        elif replicon_id := request.query_params.get("replicon_id"):
            queryset = self.queryset.filter(replicon_id=replicon_id)
        elif replicon_acc := request.query_params.get("replicon_acc"):
            queryset = models.GeneSegment.objects.select_related(
                "gene__replicon"
            ).filter(gene__replicon__accession=replicon_acc)
        else:
            return Response(
                {"detail": "Searchable field is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sample_data = []
        # TODO : check for mulitple cds's per gene
        # raise NotImplementedError("Multiple CDS per gene not implemented")
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
            _data["gene.gene_symbol"] = item.gene.symbol
            _data["gene.gene_accession"] = item.gene.accession
            _data["gene.gene_sequence"] = item.gene.sequence
            _data["gene_segment.id"] = item.id
            _data["gene_segment.gene_id"] = item.gene_id
            _data["gene_segment.start"] = item.start
            _data["gene_segment.end"] = item.end
            _data["gene_segment.forward_strand"] = item.forward_strand
            _data["gene_segment.order"] = item.order

            # Add CDS information
            cds_list = []
            for cds in item.gene.cds_set.all():
                cds_data = {
                    "cds.id": cds.id,
                    "cds.accession": cds.accession,
                    "cds.sequence": cds.sequence,
                    "cds.description": cds.description,
                }
                cds_segments = []
                for segment in cds.cds_segments.all():
                    segment_data = {
                        "cds_segment.id": segment.id,
                        "cds_segment.order": segment.order,
                        "cds_segment.start": segment.start,
                        "cds_segment.end": segment.end,
                        "cds_segment.forward_strand": segment.forward_strand,
                    }
                    cds_segments.append(segment_data)
                cds_data["cds_segments"] = cds_segments

                # Add Peptide information
                peptide_list = []
                for peptide in cds.peptides.all():
                    peptide_data = {
                        "peptide.id": peptide.id,
                        "peptide.description": peptide.description,
                        "peptide.type": peptide.type,
                    }
                    peptide_segments = []
                    for segment in peptide.peptide_segments.all().order_by("order"):
                        segment_data = {
                            "peptide_segment.id": segment.id,
                            "peptide_segment.order": segment.order,
                            "peptide_segment.start": segment.start,
                            "peptide_segment.end": segment.end,
                        }
                        peptide_segments.append(segment_data)
                    peptide_data["peptide_segments"] = peptide_segments
                    peptide_list.append(peptide_data)
                cds_data["peptide_list"] = peptide_list

                cds_list.append(cds_data)
            _data["cds_list"] = cds_list

            sample_data.append(_data)
        # sample_data =queryset.values()
        return Response(data=sample_data, status=status.HTTP_200_OK)


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
            return Response(
                {"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST
            )
        if "translation_id" not in request.data:
            return Response(
                {"detail": "No translation_id provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        translation_id = int(request.data.get("translation_id"))
        enable_segment = strtobool(request.data.get("segment"))
        # if enable_segment:
        #     gbk_files = request.FILES.getlist("gbk_file")
        #     import_gbk_files(gbk_files, translation_id)
        # else:
        gbk_file = request.FILES.getlist("gbk_file")
        import_gbk_file(gbk_file, translation_id)

        return Response(
            {"detail": "File uploaded successfully"}, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["get"])
    def dataset_options(self, request, *args, **kwargs):
        """
        For each organism in the Reference table, returns the corresponding
        accession values found int the Reference table and
        dataset values found in the Sample table.
        """
        queryset = models.Sample.objects.values(
            accession=F("sequence__alignments__replicon__reference__accession"),
            organism=F("sequence__alignments__replicon__reference__organism"),
            data_set_value=F("data_set"),
        ).distinct()

        result = {}

        for reference in queryset:
            organism = reference["organism"]
            accession = reference["accession"]
            data_set_value = reference["data_set_value"]

            if organism not in result:
                result[organism] = {"accessions": set(), "data_sets": set()}
            if accession is not None:
                result[organism]["accessions"].add(accession)
            if data_set_value is not None:
                result[organism]["data_sets"].add(data_set_value)

        return Response(
            result,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def delete_reference(self, request: Request, *args, **kwargs):
        if "accession" not in request.data:
            return Response(
                {"detail": "No accession provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        accession = request.data.get("accession")

        data = delete_reference(accession)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def distinct_accessions(self, request: Request, *args, **kwargs):
        accession_list = models.Reference.objects.values_list(
            "accession", flat=True
        ).distinct()
        return Response(data=accession_list, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def get_all_references(self, request: Request, *args, **kwargs):
        queryset = models.Reference.objects.all()
        sample_data = queryset.values()
        return Response(data=sample_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def get_reference_file(self, request: Request, *args, **kwargs):
        reference = request.query_params.get("reference")
        # get Reference and extract name (path)
        queryset = models.Reference.objects.filter(accession=reference)
        if queryset.exists():
            reference_obj = queryset.first()
            reference_files = reference_obj.name.split(
                ", "
            )  # Split the stored file paths

            # Fetch associated replicon accessions
            replicons = models.Replicon.objects.filter(reference=reference_obj)
            replicon_accessions = list(replicons.values_list("accession", flat=True))
            if len(reference_files) == 1:
                # Only one file, send it directly
                reference_file = reference_files[0]
                response = FileResponse(
                    open(reference_file, "rb"),
                    as_attachment=True,
                    filename=os.path.basename(reference_file),
                )

                # Add replicon_accessions to the response headers
                response["Replicon-Accessions"] = ",".join(replicon_accessions)
                return response
            else:
                # Multiple files -> Zip them
                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for ref_file in reference_files:
                        with open(ref_file, "rb") as f:
                            zipf.writestr(os.path.basename(ref_file), f.read())

                zip_buffer.seek(0)

                response = FileResponse(
                    zip_buffer,
                    as_attachment=True,
                    filename=f"{reference}.segment.zip",
                    content_type="application/zip",
                )
                # Add replicon_accessions to the response headers
                response["Replicon-Accessions"] = ",".join(replicon_accessions)
                return response
        else:
            return Response(
                {"detail": "No reference found"}, status=status.HTTP_404_NOT_FOUND
            )

    # multilple get in one.


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
            return Response(
                "No property_name provided.", status=status.HTTP_400_BAD_REQUEST
            )
        sample_property_fields = [
            field.name for field in models.Sample._meta.get_fields()
        ]
        if property_name in sample_property_fields:
            queryset = models.Sample.objects.all()
            queryset = queryset.distinct(property_name)
            return Response(
                {"values": [getattr(item, property_name) for item in queryset]},
                status=status.HTTP_200_OK,
            )
        queryset = models.Sample2Property.objects.filter(property__name=property_name)
        datatype = queryset[0].property.datatype
        queryset = queryset.distinct(datatype)
        return Response(
            {"values": [getattr(item, datatype) for item in queryset]},
            status=status.HTTP_200_OK,
        )

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
        return Response(data={"collection_dates": date_list}, status=status.HTTP_200_OK)

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
        return Response(data={"countries": country_list}, status=status.HTTP_200_OK)

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
        return Response(
            data={"sequencing_techs": sequencing_tech_list}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"])
    def distinct_property_names(self, request: Request, *args, **kwargs):
        property_names = self.get_distinct_property_names()
        return Response(
            data={"property_names": property_names}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"])
    def add_property(self, request: Request, *args, **kwargs):
        name = request.data.get("name")
        datatype = request.data.get("datatype", None)
        querytype = request.data.get("querytype", None)
        description = request.data.get("description", None)
        default = parse_default_data(request.data.get("default", None))
        obj, created = find_or_create_property(
            name=name,
            datatype=datatype,
            querytype=querytype,
            description=description,
            default=default,
        )

        if created:
            return Response(
                {"detail": "Property added successfully"},
                status=status.HTTP_201_CREATED,
            )
        elif obj:
            return Response(
                {"detail": "Property already exists"}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "Failed to add property"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def delete_property(self, request: Request, *args, **kwargs):
        name = request.data.get("name")
        deleted = delete_property(name)

        if deleted is not False:
            if deleted == 0:
                return Response(
                    {"detail": "No matching property found for deletion"},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"detail": "Property deleted successfully"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"detail": "Error occurred, please inform the admin."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
            {
                "name": "name",
                "query_type": "value_varchar",
                "description": "sample name or ID (fixed prop.)",
                "default": None,
            },
            {
                "name": "genomic_profiles",
                "query_type": "value_varchar",
                "description": "list of neuclotide mutation (fixed prop.)",
                "default": None,
            },
            {
                "name": "proteomic_profiles",
                "query_type": "value_varchar",
                "description": "list of amino acid mutation (fixed prop.)",
                "default": None,
            },
            {
                "name": "collection_date",
                "query_type": "value_date",
                "description": "Date when the sample was collected (predefined prop.)",
                "default": None,
            },
            {
                "name": "length",
                "query_type": "value_integer",
                "description": "Length of the genetic sequence (predefined prop.)",
                "default": None,
            },
            {
                "name": "lab",
                "query_type": "value_varchar",
                "description": "Name of the laboratory where the sample was analyzed (predefined prop.)",
                "default": None,
            },
            {
                "name": "zip_code",
                "query_type": "value_varchar",
                "description": "ZIP code of the location where the sample was collected (predefined prop.)",
                "default": None,
            },
            {
                "name": "host",
                "query_type": "value_varchar",
                "description": "Host organism from which the sample was taken (e.g., Human) (predefined prop.)",
                "default": None,
            },
            {
                "name": "genome_completeness",
                "query_type": "value_varchar",
                "description": "Completeness of the genome (e.g., partial or complete) (predefined prop.)",
                "default": None,
            },
            {
                "name": "lineage",
                "query_type": "value_varchar",
                "description": "Lineage (predefined prop.)",
                "default": None,
            },
            {
                "name": "sequencing_tech",
                "query_type": "value_varchar",
                "description": "Technology used for sequencing the genome (predefined prop.)",
                "default": None,
            },
            {
                "name": "country",
                "query_type": "value_varchar",
                "description": "Country where the sample was collected (predefined prop.)",
                "default": None,
            },
            {
                "name": "init_upload_date",
                "query_type": "value_date",
                "description": "Date when the sample data was initially uploaded to the database (fixed prop.)",
                "default": "current date and time",
            },
            {
                "name": "last_update_date",
                "query_type": "value_date",
                "description": "Date when the sample data was last updated in the database (fixed prop.)",
                "default": "current date and time",
            },
            {
                "name": "data_set",
                "query_type": "value_varchar",
                "description": "Name of the data set",
                "default": None,
            },
        ]  # from SAMPLE TABLE

        cols = [
            "name",
            "query_type",
            "description",
            "default",
        ]

        for _property_queryset in models.Property.objects.all():
            data_list.append(
                {
                    "name": _property_queryset.name,
                    "query_type": _property_queryset.datatype,
                    "description": _property_queryset.description,
                    "default": _property_queryset.default,
                }
            )
        data = {"keys": cols, "values": data_list}
        return Response(data=data, status=status.HTTP_200_OK)

    @staticmethod
    def get_distinct_property_names():
        queryset = models.Property.objects.all()
        queryset = queryset.distinct("name")
        filter_list = ["id", "datahash", "properties"]
        property_names = [item.name for item in queryset]
        sample_properties = [
            field.name
            for field in models.Sample._meta.get_fields()
            if field.name not in filter_list
        ]
        property_names += sample_properties
        return property_names

    @staticmethod
    def get_custom_property_names():
        queryset = models.Property.objects.all()
        queryset = queryset.distinct("name")
        property_names = [item.name for item in queryset]
        return property_names


# class AAMutationViewSet(
#     viewsets.GenericViewSet,
#     generics.mixins.ListModelMixin,
# ):
#     # input sequencing_tech list, country list, gene list, include partial bool,
#     # reference_value int, min_nb_freq int = 1?
#     queryset = models.Replicon.objects.all()

#     @action(detail=False, methods=["get"])
#     def mutation_frequency(self, request: Request, *args, **kwargs):
#         country_list = request.query_params.getlist("countries")
#         sequencing_tech_list = request.query_params.getlist("seq_techs")
#         gene_list = request.query_params.getlist("genes")
#         include_partial = bool(request.query_params.get("include_partial"))
#         reference_value = request.query_params.get("reference_value")
#         min_nb_freq = request.query_params.get("min_nb_freq")

#         samples_query = models.Sample.objects.filter(
#             sample2property__property__name="COUNTRY",
#             sample2property__value_text__in=country_list,
#         ).filter(
#             sample2property__property__name="SEQ_TECH",
#             sample2property__value_text__in=sequencing_tech_list,
#         )
#         if not include_partial:
#             samples_query.filter(
#                 sample2property__property__name="GENOME_COMPLETENESS",
#                 sample2property__value_text="complete",
#             )
#         mutation_query = (
#             models.Mutation.objects.filter(
#                 element__molecule__reference__accession=reference_value
#             )
#             .filter(alignments__sequence__sample_set__in=samples_query)
#             .filter(element__symbol__in=gene_list)
#             .annotate(mutation_count=Count("alignments__sequence__sample_set"))
#             .filter(mutation_count__gte=min_nb_freq)
#             .order_by("-mutation_count")
#         )
#         response = [
#             {
#                 "symbol": mutation.element.symbol,
#                 "mutation": mutation.label,
#                 "count": mutation.mutation_count,
#             }
#             for mutation in mutation_query
#         ]

#         return Response(data=response, status=status.HTTP_200_OK)


class ResourceViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def get_translation_table(self, request: Request):
        # file path -> resource/1.tt

        file_path = os.path.join("resource", "1.tt")
        try:
            with open(file_path, "rb") as file:
                translation_table = pickle.load(file)
        except FileNotFoundError:
            return Response(
                {"detail": "error: File not found"}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(data=translation_table)


class FileUploadViewSet(viewsets.ViewSet):

    def _convert_property_column_mapping(
        self, column_mapping: dict[str, str]
    ) -> dict[str, PropertyColumnMapping]:
        return {
            db_property_name: PropertyColumnMapping(**db_property_info)
            for db_property_name, db_property_info in column_mapping.items()
        }

    @action(detail=False, methods=["post"])
    def import_upload(self, request, *args, **kwargs):
        # Step 1: Check if zip file is present in the request
        if "zip_file" not in request.FILES:
            return Response(
                {"detail": "No zip file uploaded."}, status=status.HTTP_400_BAD_REQUEST
            )

        zip_file = request.FILES.get("zip_file")
        jobID = request.data.get("job_id", None)
        # Generate jobID if not provided
        if jobID is None or jobID == "":
            jobID = "backend_" + str(uuid.uuid4())  # 32 chars

        # Step 2: Check if this is a property upload (based on jobID)
        if "_prop" in jobID:
            # Property upload: Check for sample_id_column and column_mapping
            sample_id_column = request.data.get("sample_id_column")
            column_mapping_json = request.data.get("column_mapping")

            # Validate sample_id_column
            if not sample_id_column:
                return Response(
                    {"detail": "No sample_id_column is provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate column_mapping
            if not column_mapping_json:
                return Response(
                    {"detail": "No column_mapping is provided, nothing to import."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Convert column_mapping from JSON to dict
            column_mapping = self._convert_property_column_mapping(
                json.loads(column_mapping_json)
            )
            if not column_mapping:
                return Response(
                    {"detail": "No column_mapping could be processed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            filename = (
                datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]
                + "."
                + jobID
            )
            pickle_path = os.path.join(SONAR_DATA_ENTRY_FOLDER, f"{filename}.pkl")
            with open(pickle_path, "wb") as pickle_file:
                # Save the sample_id_column and column_mapping as a dictionary
                pickle.dump(
                    {
                        "sample_id_column": sample_id_column,
                        "column_mapping": column_mapping,
                    },
                    pickle_file,
                )
            # after save the pickle
            filename = filename + ".zip"
        else:
            filename = (
                datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]
                + "."
                + str(uuid.uuid4().hex)[:6]
                + ".zip"
            )

        # Step 3: Save the zip file
        save_path = os.path.join(SONAR_DATA_ENTRY_FOLDER, filename)
        with open(save_path, "wb") as destination:
            for chunk in zip_file.chunks():
                destination.write(chunk)

        # Extract files from the BytesIO
        # with zipfile.ZipFile(zip_file, "r") as zip_ref:
        #     zip_ref.extractall(SONAR_DATA_ENTRY_FOLDER)
        # to view list of files and file details in ZIP
        # for file_info in zip_ref.infolist():
        #    print(file_info)
        LOGGER.debug(f"jobID: {jobID}")
        try:
            proJobID_obj = models.ProcessingJob.objects.get(job_name=jobID)
            LOGGER.debug(f"ProcessingJob object: {proJobID_obj}")
        except:
            LOGGER.debug(f"object with job id={jobID} does not exist yet")
        LOGGER.debug("Continuing processing...")

        # Step 4: Register job in database
        try:
            proJobID_obj, _ = models.ProcessingJob.objects.get_or_create(
                status="Q", job_name=jobID
            )
        except IntegrityError as e:
            proJobID_obj = models.ProcessingJob.objects.get(job_name=jobID)

        models.FileProcessing.objects.create(
            file_name=filename, processing_job_id=proJobID_obj.id
        )
        check_for_new_data()
        return Response(
            {"detail": "File uploaded successfully", "jobID": jobID},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def start_file_import(self, request, *args, **kwargs):
        check_for_new_data()
        return Response(
            {"detail": "File uploaded successfully"}, status=status.HTTP_201_CREATED
        )


class LineageViewSet(
    viewsets.GenericViewSet,
    generics.mixins.ListModelMixin,
    generics.mixins.RetrieveModelMixin,
):
    model = models.Lineage
    queryset = models.Lineage.objects.all()
    serializer_class = LineagesSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name", "parent"]

    @action(detail=True, methods=["get"])
    def get_sublineages(self, request: Request, *args, **kwargs):
        lineage = self.get_object()
        sublineages = lineage.get_sublineages()
        print(len(sublineages))
        list = [str(lineage) for lineage in sublineages]
        list.sort()
        return Response(data={"sublineages": list}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def distinct_lineages(self, request: Request, *args, **kwargs):
        distinct_lineages = models.Lineage.objects.values_list(
            "name", flat=True
        ).distinct()
        return Response(
            {"lineages": distinct_lineages},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["put"])
    def update_lineages(self, request: Request, *args, **kwargs):
        tsv_file = request.FILES.get("lineages_file")
        tsv_file = self._temp_save_file(tsv_file)
        lineage_import = LineageImport()
        lineage_import.set_file(tsv_file)
        models.Lineage.objects.all().delete()
        lineage_import.process_lineage_data()
        return Response(
            {"detail": "Lineages updated successfully"}, status=status.HTTP_200_OK
        )

    def _temp_save_file(self, uploaded_file: InMemoryUploadedFile):
        file_path = os.path.join(SONAR_DATA_ENTRY_FOLDER, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        return file_path


class TasksView(
    viewsets.GenericViewSet,
):
    serializer_class = (
        ProcessingJobSerializer  # Specify the serializer class for the model
    )

    @action(detail=False, methods=["get"])  # detail=False means it's a list action
    def generate_job_id(self, request, *args, **kwargs):
        is_prop = strtobool(request.query_params.get("is_prop", "False"))
        job_id = generate_job_ID(is_prop)

        return Response(data={"job_id": job_id}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])  # detail=False means it's a list action
    def get_all_jobs(self, request, *args, **kwargs):
        # Retrieve all ProcessingJob instances
        jobs = models.ProcessingJob.objects.all()
        # Serialize the queryset
        serializer = self.get_serializer(jobs, many=True)
        # Return serialized data in the response
        return Response(data={"detail": serializer.data}, status=status.HTTP_200_OK)

    # get by job id
    @action(detail=False, methods=["get"])
    def get_files_by_job_id(self, request, *args, **kwargs):
        try:
            if job_id := request.query_params.get("job_id"):
                jobID_obj = models.ProcessingJob.objects.get(job_name=job_id)
            else:
                return Response(
                    {"detail": "job_id field is missing"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Retrieve all FileProcessing instances associated with the job
            files = models.FileProcessing.objects.filter(
                processing_job__job_name=job_id
            )
            # Serialize the FileProcessing instances
            # file_serializer = FileProcessingSerializer(files, many=True)

            # # Retrieve ImportLog instances for each file and their status

            files_data = []
            for file in files:
                logs = models.ImportLog.objects.filter(file=file)
                logs_data = ImportLogSerializer(logs, many=True).data
                files_data.append(
                    {"file_name": file.file_name, "status_list": logs_data}
                )
            return Response(
                data={
                    "jobID": job_id,
                    "status": jobID_obj.status,
                    "detail": files_data,
                },
                status=status.HTTP_200_OK,
            )
        except models.ProcessingJob.DoesNotExist:
            return Response(
                data={"detail": f"Job not found ({job_id})"},
                status=status.HTTP_400_BAD_REQUEST,
            )
