from datetime import datetime
from django.db import models
from django.db.models import UniqueConstraint


class Sequence(models.Model):
    seqhash = models.CharField(unique=True, max_length=200)

    class Meta:
        db_table = "sequence"


class Alignment(models.Model):
    replicon = models.ForeignKey("Replicon", models.CASCADE , blank=True, null=True)
    sequence = models.ForeignKey(
        "Sequence", models.CASCADE, blank=True, null=True, related_name="alignments"
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["replicon", "sequence"],
            )
        ]
        constraints = [
            UniqueConstraint(
                name="unique_alignment",
                fields=["replicon", "sequence"],
            ),
        ]
        db_table = "alignment"


class Alignment2Mutation(models.Model):
    alignment = models.ForeignKey(Alignment, models.CASCADE)
    mutation = models.ForeignKey("Mutation", models.CASCADE, blank=True, null=True)

    class Meta:                 
        indexes = [
            models.Index(
                fields=["alignment", "mutation"],
            )
        ]
        db_table = "alignment2mutation"
        constraints = [
            UniqueConstraint(
                name="unique_alignment2mutation",
                fields=["mutation", "alignment"],
            ),
        ]


class AnnotationType(models.Model):
    seq_ontology = models.CharField(max_length=50, blank=True, null=True)
    region = models.CharField(max_length=50, blank=True, null=True)
    impact = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "annotation_type"
        constraints = [
            UniqueConstraint(
                name="unique_annotation",
                fields=["seq_ontology", "region", "impact"],
            ),
            UniqueConstraint(
                name="unique_annotation_null_region",
                fields=["seq_ontology", "impact"],
                condition=models.Q(region__isnull=True),
            ),
        ]


class Replicon(models.Model):
    length = models.BigIntegerField(blank=True, null=True)
    sequence = models.TextField(blank=True, null=True)
    accession = models.CharField(max_length=50, unique=True, blank=True, null=True)
    description = models.CharField(max_length=400, blank=True, null=True)
    type = models.CharField(max_length=50, blank=True, null=True)
    segment_number = models.BigIntegerField(blank=True, null=True)
    reference = models.ForeignKey("Reference", models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = "replicon"


class Gene(models.Model):
    description = models.CharField(max_length=100, blank=True, null=True)
    start = models.BigIntegerField(blank=True, null=True)
    end = models.BigIntegerField(blank=True, null=True)
    strand = models.BigIntegerField(blank=True, null=True)
    gene_symbol = models.CharField(max_length=50, blank=True, null=True)
    cds_symbol = models.CharField(max_length=50, blank=True, null=True)
    gene_accession = models.CharField(max_length=50, unique=True, blank=True, null=True)
    cds_accession = models.CharField(max_length=50, unique=True, blank=True, null=True)
    gene_sequence = models.TextField(blank=True, null=True)
    cds_sequence = models.TextField(blank=True, null=True)

    replicon = models.ForeignKey(Replicon, models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = "gene"


class GeneSegment(models.Model):
    gene = models.ForeignKey(Gene, models.CASCADE, blank=True, null=True)
    start = models.BigIntegerField()
    end = models.BigIntegerField()
    strand = models.BigIntegerField()
    base = models.FloatField()
    segment = models.BigIntegerField()

    class Meta:
        db_table = "gene_segment"



class Lineage(models.Model):
    prefixed_alias = models.CharField(max_length=50, blank=True, null=True)
    lineage = models.CharField(max_length=100)

    class Meta:
        db_table = "lineage"
        constraints = [
            UniqueConstraint(
                name="unique_lineage",
                fields=["prefixed_alias", "lineage"],
            ),
            UniqueConstraint(
                name="unique_lineage_null_alias",
                fields=["lineage"],
                condition=models.Q(prefixed_alias__isnull=True),      
            ),
        ]

class LineageAlias(models.Model):
    alias = models.CharField(max_length=50)
    lineage = models.ForeignKey("Lineage", models.CASCADE, blank=True, null=True)
    parent_alias = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "lineage_alias"
        constraints = [
            UniqueConstraint(
                name="unique_alias2lineage",
                fields=["alias", "lineage"],
                condition=models.Q(parent_alias__isnull=True),
            ),
            UniqueConstraint(
                name="unique_alias2parent_alias",
                fields=["alias", "parent_alias"],
                condition=models.Q(lineage__isnull=True),
            ),
        ]


class Reference(models.Model):
    name = models.CharField(max_length=50, unique=True, blank=True, null=True)
    accession = models.CharField(max_length=50, unique=True, blank=True, null=True)
    description = models.CharField(max_length=400, blank=True, null=True)
    organism = models.CharField(max_length=50, blank=True, null=True)
    mol_type = models.CharField(max_length=50, blank=True, null=True)
    isolate = models.CharField(max_length=50, blank=True, null=True)
    host = models.CharField(max_length=50, blank=True, null=True)
    db_xref = models.CharField(max_length=50, blank=True, null=True, unique=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    collection_date = models.DateField(blank=True, null=True)
    translation_id = models.IntegerField()

    class Meta:
        db_table = "reference"


class Property(models.Model):
    name = models.CharField(max_length=50, unique=True)
    datatype = models.CharField(max_length=50)
    querytype = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=400, blank=True, null=True)
    target = models.CharField(max_length=50, blank=True, null=True)
    standard = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "property"


class Sample(models.Model):
    name = models.CharField(max_length=100, unique=True, blank=True, null=True)
    datahash = models.CharField(max_length=50, blank=True, null=True)
    sequence = models.ForeignKey(
        Sequence, models.DO_NOTHING, blank=True, null=True, related_name="samples"
    )
    sequencing_tech = models.CharField(max_length=50, blank=True, null=True)
    processing_date = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    host = models.CharField(max_length=50, blank=True, null=True)
    zip_code = models.CharField(max_length=50, blank=True, null=True)
    lab = models.CharField(max_length=50, blank=True, null=True)
    lineage = models.CharField(max_length=50, blank=True, null=True)
    genome_completeness = models.CharField(max_length=50, blank=True, null=True)
    length = models.IntegerField(blank=True, null=True)
    collection_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "sample"


class Sample2Property(models.Model):
    property = models.ForeignKey(Property, models.CASCADE)
    sample = models.ForeignKey(Sample, models.CASCADE, related_name="properties")
    value_integer = models.BigIntegerField(blank=True, null=True)
    value_float = models.FloatField(blank=True, null=True)
    value_text = models.TextField(blank=True, null=True)
    value_varchar = models.CharField(max_length=400, blank=True, null=True)
    value_blob = models.BinaryField(blank=True, null=True)
    value_date = models.DateField(blank=True, null=True)
    value_zip = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "sample2property"
        constraints = [
            UniqueConstraint(
                name="unique_property2sample",
                fields=["property", "sample"],
            ),
        ]


class Mutation(models.Model):
    gene = models.ForeignKey("Gene", models.CASCADE, blank=True, null=True)
    replicon = models.ForeignKey(Replicon, models.CASCADE, blank=True, null=True)
    ref = models.CharField(max_length=5000, blank=True, null=True)
    alt = models.CharField(max_length=5000, blank=True, null=True)
    start = models.BigIntegerField(blank=True, null=True)
    end = models.BigIntegerField(blank=True, null=True)
    parent_id = models.BigIntegerField(blank=True, null=True)
    alignments = models.ManyToManyField(
        Alignment, through="Alignment2Mutation", related_name="mutations"
    )
    type = models.CharField(
        max_length=50, blank=True, null=True
    )  # cds / nt / intergenic

    class Meta:
        db_table = "mutation"
        indexes = [
            models.Index(fields=["gene"]),
            models.Index(fields=["start"]),
            models.Index(fields=["end"]),
            models.Index(fields=["ref"]),
            models.Index(fields=["alt"]),
            models.Index(fields=["type"]),
        ]
        constraints = [
            UniqueConstraint(
                name="unique_mutation",
                fields=["ref", "alt", "start", "end", "type", "gene", "replicon"],
            ),
            UniqueConstraint(
                name="unique_mutation_null_gene",
                fields=["ref", "alt", "start", "end", "type", "replicon"],
                condition=models.Q(gene__isnull=True),
            ),
            UniqueConstraint(
                name="unique_mutation_null_alt",
                fields=["ref", "start", "end", "type", "gene", "replicon"],
                condition=models.Q(alt__isnull=True),
            ),
            UniqueConstraint(
                name="unique_mutation_null_alt_null_gene",
                fields=["ref", "start", "end", "type", "replicon"],
                condition=models.Q(alt__isnull=True) & models.Q(gene__isnull=True),
            ),
        ]


class Mutation2Annotation(models.Model):
    mutation = models.ForeignKey(Mutation, models.DO_NOTHING, blank=True, null=True)
    alignment = models.ForeignKey(Alignment, models.CASCADE, blank=True, null=True)
    annotation = models.ForeignKey(
        AnnotationType, models.DO_NOTHING, blank=True, null=True
    )

    class Meta:
        db_table = "mutation2annotation"
        constraints = [
            UniqueConstraint(
                name="unique_mutation2annotation",
                fields=["mutation", "alignment", "annotation"],
            ),
        ]


class EnteredData(models.Model):
    type = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=400, blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "entered_data"
        constraints = [
            UniqueConstraint(
                name="unique_entered_data",
                fields=["type", "name"],
            ),
        ]
