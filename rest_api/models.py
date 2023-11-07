from datetime import datetime
from django.db import models
from django.db.models import UniqueConstraint


class Sequence(models.Model):
    seqhash = models.CharField(unique=True, max_length=200)

    class Meta:
        db_table = "sequence"


class Alignment(models.Model):
    replicon = models.ForeignKey("Replicon", models.DO_NOTHING, blank=True, null=True)
    sequence = models.ForeignKey(
        "Sequence", models.DO_NOTHING, blank=True, null=True, related_name="alignments"
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["replicon", "sequence"],
            )
        ]
        db_table = "alignment"


class Alignment2Mutation(models.Model):
    alignment = models.ForeignKey(Alignment, models.DO_NOTHING)
    mutation = models.ForeignKey("Mutation", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["alignment", "mutation"],
            )
        ]
        db_table = "alignment2mutation"
        unique_together = (("mutation", "alignment"),)


class AnnotationType(models.Model):
    seq_ontology = models.CharField(max_length=50, blank=True, null=True)
    region = models.CharField(max_length=50, blank=True, null=True)
    impact = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "annotation_type"


class Replicon(models.Model):
    length = models.BigIntegerField(blank=True, null=True)
    sequence = models.TextField(blank=True, null=True)
    accession = models.CharField(unique=True, blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    type = models.CharField(blank=True, null=True)
    segment_number = models.BigIntegerField(blank=True, null=True)
    reference = models.ForeignKey("Reference", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        db_table = "replicon"


class Gene(models.Model):
    description = models.CharField(blank=True, null=True)
    start = models.BigIntegerField(blank=True, null=True)
    end = models.BigIntegerField(blank=True, null=True)
    strand = models.BigIntegerField(blank=True, null=True)
    gene_symbol = models.CharField(blank=True, null=True)
    cds_symbol = models.CharField(blank=True, null=True)
    gene_accession = models.CharField(unique=True, blank=True, null=True)
    cds_accession = models.CharField(unique=True, blank=True, null=True)
    gene_sequence = models.TextField(blank=True, null=True)
    cds_sequence = models.TextField(blank=True, null=True)

    replicon = models.ForeignKey(Replicon, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        db_table = "gene"


class GeneSegment(models.Model):
    gene = models.ForeignKey(Gene, models.DO_NOTHING, blank=True, null=True)
    start = models.BigIntegerField()
    end = models.BigIntegerField()
    strand = models.BigIntegerField()
    base = models.FloatField()
    segment = models.BigIntegerField()

    class Meta:
        db_table = "gene_segment"


class Lineages(models.Model):
    lineage = models.CharField(max_length=100, unique=True)
    parent_lineage = models.ForeignKey(
        "self",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "lineages"


class Reference(models.Model):
    name = models.CharField(unique=True, blank=True, null=True)
    accession = models.CharField(unique=True, blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    organism = models.CharField(blank=True, null=True)
    mol_type = models.CharField(blank=True, null=True)
    isolate = models.CharField(blank=True, null=True)
    host = models.CharField(blank=True, null=True)
    db_xref = models.CharField(blank=True, null=True, unique=True)
    country = models.CharField(blank=True, null=True)
    collection_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "reference"


class Property(models.Model):
    name = models.CharField(unique=True)
    datatype = models.CharField()
    querytype = models.CharField(blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    target = models.CharField(blank=True, null=True)
    standard = models.CharField(blank=True, null=True)

    class Meta:
        db_table = "property"


class Sample(models.Model):
    name = models.CharField(unique=True, blank=True, null=True)
    datahash = models.CharField(blank=True, null=True)
    sequence = models.ForeignKey(
        Sequence, models.DO_NOTHING, blank=True, null=True, related_name="samples"
    )
    sequencing_tech = models.CharField(blank=True, null=True)
    processing_date = models.DateField(blank=True, null=True)
    country = models.CharField(blank=True, null=True)
    host = models.CharField(blank=True, null=True)
    zip_code = models.CharField(blank=True, null=True)
    lab = models.CharField(blank=True, null=True)
    lineage = models.CharField(blank=True, null=True)
    genome_completeness = models.CharField(blank=True, null=True)
    length = models.IntegerField(blank=True, null=True)
    collection_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "sample"


class Sample2Property(models.Model):
    property = models.ForeignKey(Property, models.DO_NOTHING)
    sample = models.ForeignKey(Sample, models.DO_NOTHING, related_name="properties")
    value_integer = models.BigIntegerField(blank=True, null=True)
    value_float = models.DecimalField(
        max_digits=10, decimal_places=10, blank=True, null=True
    )
    value_text = models.TextField(blank=True, null=True)
    value_varchar = models.CharField(blank=True, null=True)
    value_blob = models.BinaryField(blank=True, null=True)
    value_date = models.DateField(blank=True, null=True)
    value_zip = models.CharField(blank=True, null=True)

    class Meta:
        db_table = "sample2property"
        unique_together = (("property", "sample"),)


class Mutation(models.Model):
    gene = models.ForeignKey("Gene", models.DO_NOTHING, blank=True, null=True)
    replicon = models.ForeignKey(Replicon, models.DO_NOTHING, blank=True, null=True)
    ref = models.CharField(blank=True, null=True)
    alt = models.CharField(blank=True, null=True)
    start = models.BigIntegerField(blank=True, null=True)
    end = models.BigIntegerField(blank=True, null=True)
    parent_id = models.BigIntegerField(blank=True, null=True)
    alignments = models.ManyToManyField(
        Alignment, through="Alignment2Mutation", related_name="mutations"
    )
    type = models.CharField(blank=True, null=True)  # cds / nt / intergenic

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
        ]


class Mutation2Annotation(models.Model):
    mutation = models.ForeignKey(Mutation, models.DO_NOTHING, blank=True, null=True)
    alignment = models.ForeignKey(Alignment, models.DO_NOTHING, blank=True, null=True)
    annotation = models.ForeignKey(
        AnnotationType, models.DO_NOTHING, blank=True, null=True
    )

    class Meta:
        db_table = "mutation2annotation"
        unique_together = (("mutation", "alignment", "annotation"),)


class EnteredData(models.Model):
    type = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=400, blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "entered_data"
        unique_together = (("type", "name"),)
