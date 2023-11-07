from collections import OrderedDict
from typing import Type
from rest_framework import serializers
from . import models
from django.db.models import Model as DjangoModel
from rest_framework import serializers
from django.db.models import Q


def find_or_create(
    data, model: Type[DjangoModel], serializer_class: Type[serializers.Serializer]
) -> DjangoModel:
    try:
        return model.objects.get(**data)
    except model.DoesNotExist:
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.save()


class MutationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Mutation
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
    properties = Sample2PropertyBulkCreateOrUpdateSerializer(many=True, read_only=True)
    sequence = serializers.PrimaryKeyRelatedField(
        queryset=models.Sequence.objects.all()
    )

    class Meta:
        model = models.Sample
        fields = "__all__"


class ReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Reference
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
        for sequence in ["gene_sequence", "cds_sequence"]:
            if sequence in validated_data:
                validated_data[sequence] = (
                    validated_data["sequence"].strip().upper().replace("U", "T")
                )
        return super().create(validated_data)

    class Meta:
        model = models.Gene
        fields = "__all__"


class GeneSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GeneSegment
        fields = "__all__"


class SampleGenomesSerializer(serializers.ModelSerializer):
    properties = serializers.SerializerMethodField()
    genomic_profiles = serializers.SerializerMethodField()
    #proteomic_profiles = serializers.SerializerMethodField()

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
        ]

    def get_properties(self, obj: models.Sample):
        custom_properties = Sample2PropertySerializer(
            obj.properties, many=True, read_only=True
        ).data

        for prop in [
            "sequencing_tech",
            "processing_date",
            "country",
            "host",
            "zip_code",
            "lab",
            "lineage",
            "genome_completeness",
            "length",
            "collection_date",
        ]:
            if value := getattr(obj, prop):
                custom_properties.append({"name": prop, "value": value})
        return custom_properties

    def get_genomic_profiles(self, obj: models.Sample):
        # genomic_profiles are prefetched for genomes endpoint
        list = []
        for alignment in obj.sequence.alignments.all():
            list += [mutation.label for mutation in alignment.genomic_profiles]
        return list

    # def get_proteomic_profiles(self, obj: models.Sample):
    #     # proteomic_profiles are prefetched
    #     list = []
    #     for alignment in obj.sequence.alignments.all():
    #         list += [f"{alignment.gene.gene_symbol}:{mutation.label}" for mutation in alignment.proteomic_profiles]
    #     return list
