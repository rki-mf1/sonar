from collections import OrderedDict
import datetime
from typing import Type

from django.db.models import Model as DjangoModel
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers

from . import models


def find_or_create(
    data, model: Type[DjangoModel], serializer_class: Type[serializers.Serializer]
) -> DjangoModel:
    try:
        return model.objects.get(**data)
    except model.DoesNotExist:
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.save()


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Property
        fields = "__all__"
        filter_backends = [DjangoFilterBackend]


class AminoAcidMutationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AminoAcidMutation
        fields = "__all__"


class NucleotideMutationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NucleotideMutation
        fields = "__all__"


class Sample2PropertySerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Sample2Property
        fields = ["name", "value"]

    def get_value(self, obj: models.Sample2Property):
        return (
            obj.value_integer
            or obj.value_float
            or obj.value_text
            or obj.value_varchar
            or obj.value_blob
            or obj.value_date
            or obj.value_zip
        )

    def get_name(self, obj: models.Sample2Property):
        return obj.property.name


class Sample2PropertyBulkCreateOrUpdateSerializer(serializers.ModelSerializer):
    sample = serializers.PrimaryKeyRelatedField(queryset=models.Sample.objects.all())
    property = serializers.PrimaryKeyRelatedField(
        queryset=models.Property.objects.all()
    )
    value_integer = serializers.IntegerField(required=False, allow_null=True)
    value_float = serializers.FloatField(required=False, allow_null=True)
    value_text = serializers.CharField(required=False, allow_null=True)
    value_varchar = serializers.CharField(required=False, allow_null=True)
    value_blob = serializers.CharField(required=False, allow_null=True)
    value_date = serializers.DateField(required=False, allow_null=True)
    value_zip = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = models.Sample2Property
        fields = [
            "property",
            "sample",
            "value_integer",
            "value_float",
            "value_text",
            "value_varchar",
            "value_blob",
            "value_date",
            "value_zip",
        ]
        optional_fields = [
            "value_integer",
            "value_float",
            "value_text",
            "value_varchar",
            "value_blob",
            "value_date",
            "value_zip",
        ]

    def validate(self, data: OrderedDict):
        if not any(attr in data for attr in self.Meta.optional_fields):
            raise serializers.ValidationError(
                "At least one of the following fields must be provided: "
                + ", ".join(self.Meta.optional_fields)
            )
        datatype = [key for key in data.keys() if key in self.Meta.optional_fields][0]
        if "property__name" in data:
            data["property"] = models.Property.objects.get_or_create(
                name=data.pop("property__name"), datatype=datatype
            )[0]
        return data

    def get_unique_together_validators(self):
        """Overriding method to disable unique together checks"""
        return []


class SequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Sequence
        fields = "__all__"


class SampleSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    sequence = serializers.PrimaryKeyRelatedField(
        queryset=models.Sequence.objects.all()
    )

    class Meta:
        model = models.Sample
        fields = "__all__"
        lookup_field = "name"


class ReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Reference
        fields = "__all__"


class AlignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Alignment
        fields = "__all__"


class RepliconSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        validated_data["sequence"] = (
            validated_data["sequence"].strip().upper().replace("U", "T")
        )
        return super().create(validated_data)

    class Meta:
        model = models.Replicon
        fields = "__all__"


class GeneSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        if "sequence" in validated_data:
            validated_data["sequence"] = (
                validated_data["sequence"].strip().upper().replace("U", "T")
            )
        return super().create(validated_data)

    class Meta:
        model = models.Gene
        fields = "__all__"


class CDSSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CDS
        fields = "__all__"


class CDSSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CDSSegment
        fields = "__all__"


class PeptideSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Peptide
        fields = "__all__"


class PeptideSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PeptideSegment
        fields = "__all__"


class GeneSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GeneSegment
        fields = "__all__"


class SampleGenomesSerializer(serializers.ModelSerializer):
    properties = serializers.SerializerMethodField()
    genomic_profiles = serializers.SerializerMethodField()
    proteomic_profiles = serializers.SerializerMethodField()

    class Meta:
        model = models.Sample
        fields = [
            "id",
            "name",
            "sequence_id",
            "datahash",
            "properties",
            "genomic_profiles",
            "proteomic_profiles",
            "init_upload_date",
            "last_update_date",
        ]

    def get_properties(self, obj: models.Sample):
        custom_properties = Sample2PropertySerializer(
            obj.properties, many=True, read_only=True
        ).data
        filter_list = ["properties", "name", "sequence", "id", "datahash"]
        sample_properties = [
            field.name
            for field in models.Sample._meta.get_fields()
            if field.name not in filter_list
        ]
        for prop in sample_properties:
            if value := getattr(obj, prop):
                if type(value) == datetime.datetime:
                    value = value.strftime("%Y-%m-%d")
                custom_properties.append({"name": prop, "value": value})
        return custom_properties

    def get_genomic_profiles(self, obj: models.Sample):
        # genomic_profiles are prefetched for genomes endpoint
        dict = {}

        for alignment in obj.sequence.alignments.all():
            for mutation in alignment.genomic_profiles:
                annotations = []
                for nucleotide_mutation in alignment.nucleotide_mutations.all():
                    if nucleotide_mutation == mutation:
                        for annotation in nucleotide_mutation.alignment_annotations:
                            annotations.append(str(annotation))
                dict[self.create_NT_format(mutation)] = annotations
        return dict

    def define_proteomic_label(
        self,
        mutation: models.NucleotideMutation,
        gene_symbol: str,
        mutation_start: int,
        mutation_end: int,
    ):
        # SNP and INS
        if mutation.alt != "":
            label = f"{gene_symbol}:{mutation.ref}{mutation_end}{mutation.alt}"
        else:  # DEL
            if mutation_end - mutation_start == 1:
                label = f"{gene_symbol}:del:" + str(mutation_start + 1)
            else:
                label = (
                    f"{gene_symbol}:del:"
                    + str(mutation_start + 1)
                    + "-"
                    + str(mutation_end)
                )
        return label

    def get_proteomic_profiles(self, obj: models.Sample):
        # proteomic_profiles are prefetched
        label_list = []
        alignments = obj.sequence.alignments.prefetch_related(
            "amino_acid_mutations__cds__gene",
        )
        for alignment in alignments:
            for mutation in alignment.amino_acid_mutations.all():
                try:
                    gene_symbol = mutation.cds.gene.symbol
                    mutation_start = mutation.start
                    mutation_end = mutation.end
                    label = self.define_proteomic_label(
                        mutation, gene_symbol, mutation_start, mutation_end
                    )
                    label_list.append((gene_symbol, mutation_start, label))

                except AttributeError as e:
                    # most of the time this AttributeError outputs
                    # 'NoneType' object has no attribute 'gene_symbol'
                    print(e)
                    print(f"{mutation.ref}{mutation.end}{mutation.alt}")
                    continue
        sorted_label_list = [
            item[2] for item in sorted(label_list, key=lambda x: (x[0], x[1]))
        ]
        return sorted_label_list

    def create_NT_format(self, mutation: models.NucleotideMutation):
        label = ""
        # SNP and INS
        if mutation.alt != "":
            label = f"{mutation.ref}{mutation.end}{mutation.alt}"
            if mutation.is_frameshift:
                label += "*fs"
        else:  # DEL
            if mutation.end - mutation.start == 1:
                label = "del:" + str(mutation.start + 1)
            else:
                label = "del:" + str(mutation.start + 1) + "-" + str(mutation.end)
            if mutation.is_frameshift:
                label += "*fs"

        return label


class SampleGenomesSerializerVCF(serializers.ModelSerializer):
    genomic_profiles = serializers.SerializerMethodField()

    class Meta:
        model = models.Sample
        fields = ["id", "name", "genomic_profiles"]

    def get_genomic_profiles(self, obj: models.Sample):
        list = []
        for alignment in obj.sequence.alignments.all():
            for mutation in alignment.genomic_profiles:
                variant = {}
                variant["variant.id"] = mutation.id
                variant["variant.ref"] = mutation.ref
                variant["variant.alt"] = mutation.alt
                variant["variant.start"] = mutation.start
                variant["variant.end"] = mutation.end
                list.append(variant)
        return list


class SampleGenomesExportStreamSerializer(SampleGenomesSerializer):
    row = serializers.SerializerMethodField()
    columns = ["name"]

    def get_row(self, obj: models.Sample):
        custom_properties = Sample2PropertySerializer(
            obj.properties, many=True, read_only=True
        ).data
        row = []
        for column in self.columns:
            if column == "proteomic_profiles":
                row.append(", ".join(self.get_proteomic_profiles(obj)))
            elif column == "genomic_profiles":
                row.append(", ".join(list(self.get_genomic_profiles(obj).keys())))
            elif value := next(
                (item["value"] for item in custom_properties if item["name"] == column),
                None,
            ):
                row.append(value)
            else:
                try:
                    row.append(getattr(obj, column))
                except:
                    row.append("")
        return row

    class Meta:
        model = models.Sample
        fields = ["row"]


class LineagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Lineage
        fields = "__all__"


class ProcessingJobSerializer(serializers.ModelSerializer):
    # Map the abbreviations to their full names for the 'status' field
    status = serializers.CharField(source="get_status_display")
    entry_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = models.ProcessingJob
        fields = ["job_name", "status", "entry_time"]


class FileProcessingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FileProcessing
        fields = ["file_name"]  # Add more fields if needed


class ImportLogSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="get_type_display")
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = models.ImportLog
        fields = ["type", "updated", "success"]
