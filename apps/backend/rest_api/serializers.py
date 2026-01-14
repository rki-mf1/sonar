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
    sequences = serializers.PrimaryKeyRelatedField(
        queryset=models.Sequence.objects.all(), many=True
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
    sequences = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = models.Sample
        fields = [
            "id",
            "name",
            "sequences",
            "datahash",
            "properties",
            "genomic_profiles",
            "proteomic_profiles",
        ]

    def get_properties(self, obj: models.Sample):
        """
        Use prefetched_related properties
        """
        custom_properties = []

        # Get custom properties from prefetched relations
        if hasattr(obj, "properties"):
            for prop in obj.properties.all():
                value = (
                    prop.value_integer
                    or prop.value_float
                    or prop.value_text
                    or prop.value_varchar
                    or prop.value_blob
                    or prop.value_date
                    or prop.value_zip
                )
                custom_properties.append({"name": prop.property.name, "value": value})

        # Get sample fields
        important_fields = [
            "collection_date",
            "country",
            "host",
            "lab",
            "lineage",
            "sequencing_tech",
            "zip_code",
            "genome_completeness",
            "init_upload_date",
            "last_update_date",
            "data_set",
        ]

        for field_name in important_fields:
            if hasattr(obj, field_name):
                value = getattr(obj, field_name)
                if value:
                    if isinstance(value, datetime.datetime):
                        value = value.strftime("%Y-%m-%d")
                    elif isinstance(value, datetime.date):
                        value = value.strftime("%Y-%m-%d")
                    custom_properties.append({"name": field_name, "value": value})

        return custom_properties

    def get_genomic_profiles(self, obj: models.Sample):
        showNX = self.context.get("showNX", False)
        genomic_profiles_dict = {}

        for sequence in obj.sequences.all():
            for alignment in sequence.alignments.all():
                replicon = alignment.replicon
                replicon_acc = replicon.accession

                if replicon_acc not in genomic_profiles_dict:
                    genomic_profiles_dict[replicon_acc] = {}

                for mutation in getattr(alignment, "genomic_profiles", []):
                    if not showNX and ("N" in mutation.alt):
                        continue

                    annotations = []
                    for annotation in mutation.annotations.all():
                        annotations.append(str(annotation))

                    genomic_profiles_dict[replicon_acc][
                        self.create_NT_format(mutation)
                    ] = annotations

        return OrderedDict(sorted(genomic_profiles_dict.items()))

    def get_proteomic_profiles(self, obj: models.Sample):
        """
        Use prefetched proteomic_profiles
        """
        showNX = self.context.get("showNX", False)
        proteomic_profiles = {}

        for sequence in obj.sequences.all():
            for alignment in sequence.alignments.all():
                cds_mutations = {}

                for mutation in getattr(alignment, "proteomic_profiles", []):
                    if not showNX and ("X" in mutation.alt):
                        continue

                    cds = mutation.cds
                    replicon_acc = cds.gene.replicon.accession
                    key = f"{replicon_acc}: {cds.accession}"

                    if key not in cds_mutations:
                        cds_mutations[key] = []

                    gene_symbol = cds.gene.symbol
                    label = self.define_proteomic_label(
                        mutation, gene_symbol, mutation.start, mutation.end
                    )

                    cds_mutations[key].append((gene_symbol, mutation.start, label))

                for key, labels in cds_mutations.items():
                    if key not in proteomic_profiles:
                        proteomic_profiles[key] = []
                    sorted_labels = [
                        item[2] for item in sorted(labels, key=lambda x: (x[0], x[1]))
                    ]
                    proteomic_profiles[key].extend(sorted_labels)

        return OrderedDict(sorted(proteomic_profiles.items()))

    def define_proteomic_label(
        self,
        mutation: models.AminoAcidMutation,
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
        showNX = self.context.get("showNX", False)
        replicon_dict = {}
        for sequence in obj.sequences.all():
            replicon_accession = sequence.alignments.first().replicon.accession
            if replicon_accession not in replicon_dict:
                replicon_dict[replicon_accession] = []
            for alignment in sequence.alignments.all():
                for mutation in alignment.genomic_profiles:
                    if not showNX and ("N" in mutation.alt):
                        continue
                    variant = {}
                    variant["variant.id"] = mutation.id
                    variant["variant.ref"] = mutation.ref
                    variant["variant.alt"] = mutation.alt
                    variant["variant.start"] = mutation.start
                    variant["variant.end"] = mutation.end
                    replicon_dict[replicon_accession].append(variant)
        return replicon_dict


class SampleGenomesExportStreamSerializer(SampleGenomesSerializer):
    row = serializers.SerializerMethodField()
    columns = ["name"]

    def get_row(self, obj: models.Sample):
        showNX = self.context.get("showNX", False)
        ctx = self.context

        # Initialize caches once
        if "custom_prop_cache" not in ctx:
            ctx["custom_prop_cache"] = {}
        if "genomic_cache" not in ctx:
            ctx["genomic_cache"] = {}
        if "proteomic_cache" not in ctx:
            ctx["proteomic_cache"] = {}

        # Cache custom properties
        if obj.id not in ctx["custom_prop_cache"]:
            props = []
            if hasattr(obj, "properties"):
                for prop in obj.properties.all():
                    value = (
                        prop.value_integer
                        or prop.value_float
                        or prop.value_text
                        or prop.value_varchar
                        or prop.value_blob
                        or prop.value_date
                        or prop.value_zip
                    )
                    props.append({"name": prop.property.name, "value": value})
            ctx["custom_prop_cache"][obj.id] = {p["name"]: p["value"] for p in props}

        custom_properties = ctx["custom_prop_cache"][obj.id]

        # Cache genomic profiles
        if obj.id not in ctx["genomic_cache"]:
            ctx["genomic_cache"][obj.id] = self.get_genomic_profiles(obj)

        genomic_dict = ctx["genomic_cache"][obj.id]

        # Cache proteomic profiles
        if obj.id not in ctx["proteomic_cache"]:
            ctx["proteomic_cache"][obj.id] = self.get_proteomic_profiles(obj)

        proteomic_dict = ctx["proteomic_cache"][obj.id]

        row = []
        for column in self.columns:
            if column.startswith("proteomic_profile"):
                gene_acc = column.split(": ", 1)[1]
                row.append(", ".join(proteomic_dict.get(gene_acc, [])))
            elif column.startswith("genomic_profile"):
                replicon_acc = column.split(": ", 1)[1]
                muts = genomic_dict.get(replicon_acc)
                row.append(", ".join(list(muts.keys())) if muts else "")
            elif column in custom_properties:
                row.append(custom_properties[column])
            else:
                row.append(getattr(obj, column, ""))
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
