from functools import reduce
import json
import operator
import os
import uuid
import pickle

from dataclasses import dataclass

from rest_framework import generics
import zipfile
from datetime import datetime

from django.db.utils  import IntegrityError
from django.db.models import Count, F, Q
from covsonar_backend.settings import SONAR_DATA_ENTRY_FOLDER
from django_filters.rest_framework import DjangoFilterBackend
from rest_api.data_entry.property_job import delete_property, find_or_create_property
from rest_api.data_entry.reference_job import delete_reference

from rest_api.utils import (
    write_to_file,
)
from rest_framework import generics, serializers, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.request import Request
from rest_framework.response import Response

from rest_framework import status


from rest_api.data_entry.gbk_import import import_gbk_file
from rest_api.data_entry.sample_entry_job import check_for_new_data

from . import models
from .serializers import (
    AlignmentSerializer,
    FileProcessingSerializer,
    GeneSerializer,
    ImportLogSerializer,
    ProcessingJobSerializer,
    PropertySerializer,
    ReferenceSerializer,
    MutationSerializer,
    RepliconSerializer,
    LineagesSerializer,
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
        queryset = models.Replicon.objects.distinct("accession").values("accession")
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(molecule__reference__accession=ref)
        return Response(
            {"accessions": [item["accession"] for item in queryset]},
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
        queryset = models.Gene.objects.distinct("gene_symbol").values("gene_symbol")
        if ref := request.query_params.get("reference"):
            queryset = queryset.filter(molecule__reference__accession=ref)
        return Response(
            {"gene_symbols": [item["gene_symbol"] for item in queryset]},
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
        else:
            return Response(
                {"detail": "Searchable field is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        return Response(data=sample_data, status=status.HTTP_200_OK)


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
        return Response(
            {"alts": [item["alt"] for item in queryset]}, status=status.HTTP_200_OK
        )


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
        gbk_file = request.FILES.get("gbk_file")
        import_gbk_file(gbk_file, translation_id)
        return Response(
            {"detail": "File uploaded successfully"}, status=status.HTTP_201_CREATED
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
        queryset = models.Reference.objects.all()
        accession = [item.accession for item in queryset]
        return Response(data=accession, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def get_all_references(self, request: Request, *args, **kwargs):
        queryset = models.Reference.objects.all()
        sample_data = queryset.values()
        return Response(data=sample_data, status=status.HTTP_200_OK)

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
        .annotate(count=Count("alignments__sequence__sample"))
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
        queryset = models.Property.objects.all()
        queryset = queryset.distinct("name")
        property_names = [item.name for item in queryset]
        sample_properties = models.Sample._meta.get_fields()
        property_names += [item.name for item in sample_properties]
        return Response(
            data={"property_names": property_names}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"])
    def add_property(self, request: Request, *args, **kwargs):
        name = request.data.get("name")
        datatype = request.data.get("datatype", None)
        querytype = request.data.get("querytype", None)
        description = request.data.get("description", None)

        obj, created = find_or_create_property(
            name=name, datatype=datatype, querytype=querytype, description=description
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
                "name": "collection_date",
                "query_type": "value_date",
                "description": "Collected date of sample",
            },
            {
                "name": "length",
                "query_type": "value_integer",
                "description": "Length of sequence",
            },
            {"name": "lab", "query_type": "value_varchar", "description": ""},
            {"name": "zip_code", "query_type": "value_varchar", "description": ""},
            {
                "name": "host",
                "query_type": "value_varchar",
                "description": "A host (e.g., Human)",
            },
            {
                "name": "genome_completeness",
                "query_type": "value_varchar",
                "description": "Genome completeness (partial/complete)",
            },
            {"name": "lineage", "query_type": "value_varchar", "description": ""},
            {
                "name": "sequencing_tech",
                "query_type": "value_varchar",
                "description": "",
            },
            {"name": "processing_date", "query_type": "value_date", "description": ""},
            {"name": "country", "query_type": "value_varchar", "description": ""},
        ]  # from SAMPLE TABLE
        cols = [
            "name",
            "query_type",
            "description",
        ]

        for _property_queryset in models.Property.objects.all():
            data_list.append(
                {
                    "name": _property_queryset.name,
                    "query_type": _property_queryset.datatype,
                    "description": _property_queryset.description,
                }
            )
        data = {"keys": cols, "values": data_list}
        return Response(data=data, status=status.HTTP_200_OK)


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
            .filter(alignments__sequence__sample_set__in=samples_query)
            .filter(element__symbol__in=gene_list)
            .annotate(mutation_count=Count("alignments__sequence__sample_set"))
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

        return Response(data=response, status=status.HTTP_200_OK)


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
    @action(detail=False, methods=["post"])
    def import_upload(self, request, *args, **kwargs):

        if "zip_file" not in request.FILES:
            return Response(
                {"detail": "No zip file uploaded."}, status=status.HTTP_400_BAD_REQUEST
            )

        zip_file = request.FILES.get("zip_file")
        jobID = request.data.get("job_id", None)
        if jobID is None or jobID == "":
            jobID = "backend_" + str(uuid.uuid4())  # 32 chars

        filename = (
            datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]
            + "."
            + str(uuid.uuid4().hex)[:6]
            + ".zip"
        )
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

        # Register job in database.
        try:
            proJobID_obj, _ = models.ProcessingJob.objects.get_or_create(
                status="Q", job_name=jobID
            )
        except (IntegrityError ) as e:
            proJobID_obj = models.ProcessingJob.objects.get(job_name=jobID)

        models.FileProcessing.objects.create(
            file_name=filename, processing_job_id=proJobID_obj.id
        )

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

    @action(detail=True, methods=["get"])
    def get_sublineages(self, request: Request, *args, **kwargs):
        lineage = self.get_object()
        sublineages = lineage.get_sublineages()
        list = [str(lineage) for lineage in sublineages]
        list.sort()
        return Response(data={"sublineages": list}, status=status.HTTP_200_OK)


class TasksView(
    viewsets.GenericViewSet,
):
    serializer_class = (
        ProcessingJobSerializer  # Specify the serializer class for the model
    )

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
                data={"jobID": job_id, "status": jobID_obj.status ,"detail": files_data},
                status=status.HTTP_200_OK,
            )
        except models.ProcessingJob.DoesNotExist:
            return Response(
                data={"detail": "Job not found"}, status=status.HTTP_400_BAD_REQUEST
            )
