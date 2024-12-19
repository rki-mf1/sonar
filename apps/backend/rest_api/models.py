from django.db import models
from django.db.models import Q
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Sequence(models.Model):
    seqhash = models.CharField(unique=True, max_length=200)

    class Meta:
        db_table = "sequence"


class Alignment(models.Model):
    replicon = models.ForeignKey("Replicon", models.CASCADE)
    sequence = models.ForeignKey("Sequence", models.CASCADE, related_name="alignments")

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


class AnnotationType(models.Model):
    seq_ontology = models.CharField(max_length=50)
    region = models.CharField(max_length=50, blank=True, null=True)
    impact = models.CharField(max_length=20)
    mutations = models.ManyToManyField("NucleotideMutation", related_name="annotations")

    def __str__(self) -> str:
        return f"{self.seq_ontology} {self.impact} {self.region if self.region else ''}".strip()

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
    sequence = models.TextField()
    accession = models.CharField(max_length=50, unique=True, blank=True, null=True)
    description = models.CharField(max_length=400, blank=True, null=True)
    type = models.CharField(max_length=50, blank=True, null=True)
    segment_number = models.BigIntegerField(blank=True, null=True)
    reference = models.ForeignKey("Reference", models.CASCADE)

    class Meta:
        db_table = "replicon"


class Gene(models.Model):
    description = models.CharField(max_length=100, blank=True, null=True)
    start = models.BigIntegerField()
    end = models.BigIntegerField()
    strand = models.BigIntegerField()
    gene_symbol = models.CharField(max_length=50, blank=True, null=True)
    cds_symbol = models.CharField(max_length=50, blank=True, null=True)
    gene_accession = models.CharField(
        max_length=50, unique=False, blank=True, null=True
    )
    cds_accession = models.CharField(max_length=50, unique=True, blank=True, null=True)
    gene_sequence = models.TextField(blank=True, null=True)
    cds_sequence = models.TextField(blank=True, null=True)
    replicon = models.ForeignKey(Replicon, models.CASCADE)

    class Meta:
        db_table = "gene"


class GeneSegment(models.Model):
    gene = models.ForeignKey(Gene, models.CASCADE)
    start = models.BigIntegerField()
    end = models.BigIntegerField()
    strand = models.BigIntegerField()
    base = models.FloatField()
    segment = models.BigIntegerField()

    class Meta:
        db_table = "gene_segment"


class Lineage(models.Model):
    name = models.CharField(max_length=50)  # not unique because of recombinants
    parent = models.ForeignKey("self", models.CASCADE, blank=True, null=True)

    def get_sublineages(self) -> set:
        lineages = set([self])
        lineages.update(
            Lineage.get_sublineages_from_list(Lineage.objects.filter(name=self.name))
        )
        return lineages

    @staticmethod
    def get_sublineages_from_list(lineages):
        lineages_set = set()
        if lineages.count() > 0:
            children = Lineage.objects.filter(parent__name__in=lineages.values("name"))
            lineages_set.update(children)
            lineages_set.update(Lineage.get_sublineages_from_list(children))
        return lineages_set

    def __str__(self) -> str:
        return self.name

    class Meta:
        db_table = "lineage"
        constraints = [
            UniqueConstraint(
                name="unique_lineage",
                fields=["name", "parent"],
            ),
            UniqueConstraint(
                name="unique_lineage_parent_null",
                fields=["name"],
                condition=models.Q(parent__isnull=True),
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
    name = models.CharField(max_length=100, unique=True)
    datahash = models.CharField(max_length=50)
    sequence = models.ForeignKey(Sequence, models.DO_NOTHING)
    sequencing_tech = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    host = models.CharField(max_length=50, blank=True, null=True)
    zip_code = models.CharField(max_length=50, blank=True, null=True)
    lab = models.CharField(max_length=50, blank=True, null=True)
    lineage = models.CharField(max_length=50, blank=True, null=True)
    genome_completeness = models.CharField(max_length=50, blank=True, null=True)
    length = models.IntegerField(blank=True, null=True)
    collection_date = models.DateField(blank=True, null=True)
    init_upload_date = models.DateTimeField(auto_now=True)
    last_update_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "sample"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["sequencing_tech"]),
            models.Index(fields=["country"]),
            models.Index(fields=["host"]),
            models.Index(fields=["zip_code"]),
            models.Index(fields=["lab"]),
            models.Index(fields=["lineage"]),
            models.Index(fields=["genome_completeness"]),
            models.Index(fields=["collection_date"]),
            models.Index(fields=["init_upload_date"]),
            models.Index(fields=["last_update_date"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:  # Check if this is an update to an existing record
            self.last_update_date = timezone.now()
        super().save(*args, **kwargs)


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


class NucleotideMutation(models.Model):
    replicon = models.ForeignKey(Replicon, models.CASCADE, blank=True, null=True)
    ref = models.TextField()
    alt = models.TextField()
    start = models.BigIntegerField()
    end = models.BigIntegerField()
    alignments = models.ManyToManyField(
        Alignment,
        related_name="nucleotide_mutations",
    )    

    def __str__(self) -> str:
        return f"{self.start}-{self.end} {self.ref}>{self.alt}"

    class Meta:
        db_table = "nucleotide_mutation"
        indexes = [
            models.Index(fields=["start"]),
            models.Index(fields=["end"]),
            models.Index(fields=["ref"]),
            models.Index(fields=["alt"]),
        ]
        constraints = [
            UniqueConstraint(
                name="unique_nt_mutation",
                fields=["ref", "alt", "start", "end", "replicon"],
            )            
        ]


class AminoAcidMutation(models.Model):
    gene = models.ForeignKey("Gene", models.CASCADE)
    replicon = models.ForeignKey(Replicon, models.CASCADE)
    ref = models.TextField()
    alt = models.TextField()
    start = models.BigIntegerField()
    end = models.BigIntegerField()
    parent = models.ManyToManyField(NucleotideMutation)
    alignments = models.ManyToManyField(
        Alignment,
        related_name="amino_acid_mutations",
    )

    def __str__(self) -> str:
        return f"{self.start}-{self.end} {self.ref}>{self.alt}"

    class Meta:
        db_table = "amino_acid_mutation"
        indexes = [
            models.Index(fields=["gene"]),
            models.Index(fields=["start"]),
            models.Index(fields=["end"]),
            models.Index(fields=["ref"]),
            models.Index(fields=["alt"]),
        ]
        constraints = [
            UniqueConstraint(
                name="unique_aa_mutation",
                fields=["ref", "alt", "start", "end", "gene", "replicon"],
            ),
        ]

class ProcessingJob(models.Model):
    class ImportType(models.TextChoices):
        QUEUED = "Q", _("Queued")
        IN_PROGRESS = "IP", _("In Progress")
        COMPLETED = "C", _("Completed")
        FAILED = "F", _("Failed")

    job_name = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=2,
        choices=ImportType.choices,
        default=ImportType.QUEUED,
    )
    entry_time = models.DateTimeField(auto_now=True, unique=True)

    class Meta:
        db_table = "processing_job"


class FileProcessing(models.Model):
    file_name = models.CharField(max_length=255, unique=True)
    processing_job = models.ForeignKey(
        "ProcessingJob", on_delete=models.CASCADE, related_name="files"
    )

    class Meta:
        db_table = "file_processing"


class ImportLog(models.Model):

    class ImportType(models.TextChoices):
        UNKNOWN = "NUL", _("Unknown")
        SAMPLE = "SMP", _("Sample")
        ANNOTATION = "ANN", _("Annotation")
        GENEBANK = "GBK", _("Genebank")
        SAMPLE_ANNOTATION_ARCHIVE = "SAA", _("Sample Annotation Archive")
        PROPERTY = "PTY", _("Property")

    type = models.CharField(
        max_length=3,
        choices=ImportType.choices,
        default=ImportType.UNKNOWN,
    )
    file = models.ForeignKey(
        FileProcessing,
        to_field="file_name",
        on_delete=models.CASCADE,
    )
    updated = models.DateTimeField(auto_now=True)
    success = models.BooleanField()
    exception_text = models.TextField(blank=True, null=True)
    stack_trace = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "import_log"
        constraints = [
            UniqueConstraint(
                name="unique_import_log",
                fields=["file", "updated"],
            ),
        ]
