from enum import Enum

from django.db import models
from django.db.models import Q
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Sequence(models.Model):
    """
    Represents a genetic sequence (sample) identified by a unique hash.

    Attributes:
        seqhash (CharField): A unique identifier for the sequence (max length 200).
    """

    seqhash = models.CharField(unique=True, max_length=200)

    class Meta:
        db_table = "sequence"


class Alignment(models.Model):
    """
    Represents an alignment between a sequence and a replicon.

    Attributes:
        replicon (ForeignKey): Reference to the associated Replicon
        sequence (ForeignKey): Reference to the Sequence aligned with Replicon

    Constraints:
        - Unique constraint on (replicon, sequence) to prevent duplicate alignments.

    Indexes:
        - Index on (replicon, sequence) to optimize queries.
    """

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
    """
    Represents an annotation for nucleotide mutations, classified using SnpEff.

    Attributes:
        seq_ontology (CharField): Sequence ontology term describing the annotation (max length 50).
        region (CharField, optional): Genomic region affected (max length 50, nullable).
        impact (CharField): Impact classification (e.g., HIGH, MODERATE, LOW) (max length 20).
        mutations (ManyToManyField): Related nucleotide mutations annotated with this type.

    Constraints:
        - Ensures unique annotations based on (seq_ontology, region, impact).
        - Allows uniqueness for (seq_ontology, impact) when region is NULL.
    """

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
    """
    Represents a replicon, a genetic element/segment/chromosome
    Filled with information from the gene bank file via gbk_import

    Attributes:
        length (BigIntegerField, optional): Length of the replicon in base pairs.
        sequence (TextField): Full nucleotide sequence of the replicon.
        accession (CharField, unique, optional): (NCBI) accession of sequence.
        description (CharField, optional): Additional description of the replicon.
        type (CharField, optional): Type of replicon (e.g., chromosome, plasmid).
        segment_number (BigIntegerField, optional): Segment number if applicable.
        reference (ForeignKey): id of linked reference genome.

    Constraints:
        - Ensures unique accession numbers if provided.
    """

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
    """
    Represents a gene located on a replicon.
    Filled with information from the gene bank file via gbk_import

    Attributes:
        description (CharField, optional): Functional description of the gene (max length 100).
        start (BigIntegerField): Start position on the replicon (counting starts with 0).
        end (BigIntegerField): End position on the replicon.
        forward_strand (BooleanField): Indicates if the gene is on the forward strand.
        symbol (CharField, optional): Gene symbol or abbreviation (max length 50).
        accession (CharField, optional): Accession id gene
        sequence (TextField, optional): Nucleotide sequence of the gene.
        replicon (ForeignKey): Reference to the replicon where the gene is located.
        type (TextChoices, optional): Classification of the gene (e.g., CDS, rRNA, tRNA).

    Constraints:
        - Ensures each gene is associated with a specific replicon.
    """

    description = models.CharField(max_length=100, blank=True, null=True)
    start = models.BigIntegerField()
    end = models.BigIntegerField()
    forward_strand = models.BooleanField()
    symbol = models.CharField(max_length=50, blank=True, null=True)
    accession = models.CharField(max_length=50, unique=False, blank=True, null=True)
    sequence = models.TextField(blank=True, null=True)
    replicon = models.ForeignKey(Replicon, models.CASCADE)

    class GeneTypes(models.TextChoices):
        CDS = "CDS"
        rRNA = "rRNA"
        tRNA = "tRNA"
        ncRNA = "ncRNA"
        misc_RNA = "misc_RNA"
        # tmRNA = "tmRNA"

    type = models.TextChoices(GeneTypes, blank=True, null=True)

    class Meta:
        db_table = "gene"


class CDS(models.Model):
    """
    Represents a Coding Sequence (CDS) associated with a gene.
    Filled with information from the gene bank file via gbk_import

    Attributes:
        accession (CharField, optional, unique): Unique accession nid of gene.
        sequence (TextField, optional): Nucleotide sequence of the CDS.
        gene (ForeignKey): Reference to the associated gene (CASCADE deletion).
        description (CharField, optional): Functional description of the CDS (max length 100).

    Constraints:
        - Ensures each CDS is linked to a specific gene.
        - Enforces uniqueness on the accession number if provided.
    """

    accession = models.CharField(max_length=50, unique=True, blank=True, null=True)
    sequence = models.TextField(blank=True, null=True)
    gene = models.ForeignKey(Gene, models.CASCADE)
    description = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "cds"


class CDSSegment(models.Model):
    """
    Represents a segment of a Coding Sequence (CDS), useful for cases where
    - a CDS is split across multiple regions of a gene
    - or multiple CDSs from one gene
    - or ribosomal slippage
    Filled with information from the gene bank file via gbk_import

    Attributes:
        cds (ForeignKey): Reference to the associated CDS (CASCADE deletion).
        order (BigIntegerField): Defines the sequential order of segments for final CDS product.
        start (BigIntegerField): Start position of the segment within the nt sequence.
        end (BigIntegerField): End position of the segment within the nt sequence.
        forward_strand (BooleanField): Indicates whether the segment is on the forward strand.

    Constraints:
        - Ensures each segment of a CDS has a unique order within the same CDS.
    """

    cds = models.ForeignKey(CDS, models.CASCADE)
    order = models.BigIntegerField()
    start = models.BigIntegerField()
    end = models.BigIntegerField()
    forward_strand = models.BooleanField()

    class Meta:
        db_table = "cds_part"
        constraints = [
            UniqueConstraint(
                name="unique_cds_part",
                fields=["cds", "order"],
            ),
        ]


class GeneSegment(models.Model):
    """
    Represents a segment of a gene, useful for split or modular genes.
    Filled with information from the gene bank file via gbk_import

    Attributes:
        gene (ForeignKey): Reference to the associated gene (CASCADE deletion).
        order (BigIntegerField): Defines the order of segments within the gene.
        start (BigIntegerField): Start position of the segment within the gene.
        end (BigIntegerField): End position of the segment within the gene.
        forward_strand (BooleanField): Indicates if the segment is on the forward strand.

    Constraints:
        - Ensures each gene segment has a unique order within its gene.
    """

    gene = models.ForeignKey(Gene, models.CASCADE)
    order = models.BigIntegerField()
    start = models.BigIntegerField()
    end = models.BigIntegerField()
    forward_strand = models.BooleanField()

    class Meta:
        db_table = "gene_segment"
        constraints = [
            UniqueConstraint(
                name="unique_gene_segment",
                fields=["gene", "order"],
            ),
        ]


class Lineage(models.Model):
    """
    Represents the hierarchical lineage information of a pathogen.
    Import via cli command and import_lineage.py

    Attributes:
        name (CharField): The name of the lineage.
        parent (ForeignKey): A reference to the parent lineage (if any), forming a tree-like structure.

    Methods:
        get_sublineages: Returns all sublineages, including direct children and recursive descendants.
        get_sublineages_from_list (static): A helper method to retrieve sublineages from a list of lineages.

    Constraints:
        - Ensures uniqueness of lineage name and parent combination.
        - Allows lineage to have unique names with a null parent.
    """

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
    """
    Represents a reference of a organism used for sequence alignment.
    Filled with information from the gene bank file via gbk_import

    Attributes:
        name (CharField, optional, unique): Name of the gene bank file (max length 50).
        accession (CharField, optional, unique): Accession number of the gene bank file (max length 50).
        description (CharField, optional): Description of the reference (max length 400).
        organism (CharField, optional): Name of the organism from which the reference is derived (max length 50).
        mol_type (CharField, optional): Type of molecule (e.g., DNA, RNA) for the reference (max length 50).
        isolate (CharField, optional): Isolate or strain information (max length 50).
        host (CharField, optional): Host organism for the reference sequence (max length 50).
        db_xref (CharField, optional, unique): Database cross-reference identifier (max length 50).
        country (CharField, optional): Country of origin of the sample (max length 50).
        collection_date (DateField, optional): Date when the sample was collected.
        translation_id (IntegerField): ID used for translation of the reference sequence.

    Constraints:
        - Ensures unique identifiers for name, accession, and db_xref.
    """

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
    """
    Represents a customizable property that can be defined by users to capture flexible data characteristics.

    Attributes:
        name (CharField, unique): The name of the property, must be unique.
        datatype (CharField): The data type of the property (e.g., integer, string, etc.).
        querytype (CharField, optional): The type of query that can be performed with the property (e.g., range, exact match).
        description (CharField, optional): A description of the property for documentation purposes.
        default (CharField, optional): provide default property value

    Constraints:
        - Ensures that the property name is unique.
    """

    name = models.CharField(max_length=50, unique=True)
    datatype = models.CharField(max_length=50)
    querytype = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=400, blank=True, null=True)
    default = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "property"


class Sample(models.Model):
    """
    Represents a sample that has undergone sequencing and via cli: alignment, mutation calling, and annotation.
    Metadata fields (sequencing_tech, country, host, zip_code, lab, lineage, collection_date, data_set) filled via metadata import of csv.
    Other fields via sample_entry_job.py, sample_import.py

    Attributes:
        name (CharField, unique): Unique identifier for the sample.
        datahash (CharField): (Not used at the moment) hash all metadata (include property metadata) for comparison before updating
        sequence (ForeignKey): The sequence associated with the sample.
        sequencing_tech (CharField, optional): Sequencing technology used.
        country (CharField, optional): Country of origin for the sample.
        host (CharField, optional): The host organism of the sample.
        zip_code (CharField, optional): The postal code where the sample was collected.
        lab (CharField, optional): The lab where the sample was processed.
        lineage (CharField, optional): Lineage identifier for the sample.
        genome_completeness (CharField, optional): Indicator of the genome completeness.
        length (IntegerField, optional): Length of the sequence in the sample.
        collection_date (DateField, optional): The date the sample was collected.
        init_upload_date (DateTimeField, auto_now=True): Timestamp of the initial upload.
        last_update_date (DateTimeField, optional): Timestamp of the last update to the sample.
        data_set (CharField, optional): The data set the sample is part of, e.g. rKI, Gisaid.
        properties (ManyToManyField, optional): User-defined properties assigned to the sample.

    Constraints:
        - Ensures that each sample has a unique name.
    """

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
    data_set = models.CharField(max_length=50, blank=True, null=True)

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
            models.Index(fields=["data_set"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:  # Check if this is an update to an existing record
            self.last_update_date = timezone.now()
        super().save(*args, **kwargs)


class Sample2Property(models.Model):
    """
    Represents a relationship between a sample and a property, allowing the association
    of multiple properties to a single sample, with flexibility in value types.

    Attributes:
        property (ForeignKey): The property being associated with the sample.
        sample (ForeignKey): The sample to which the property is associated.
        value_integer (BigIntegerField, optional): Integer value for the property.
        value_float (FloatField, optional): Floating-point value for the property.
        value_text (TextField, optional): Text value for the property.
        value_varchar (CharField, optional): Varchar value for the property.
        value_blob (BinaryField, optional): Binary data value for the property.
        value_date (DateField, optional): Date value for the property.
        value_zip (CharField, optional): Zip code value for the property.

    Constraints:
        - Ensures that each combination of property and sample is unique.
    """

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
    """
    Represents a nucleotide mutation within a replicon, storing the reference nt
    and alternative nucleotides, along with mutation position(s). Stores alignments
    that contain this mutation.

    Attributes:
        replicon (ForeignKey): The replicon in which the mutation is located.
        ref (TextField): The reference nucleotide(s) .
        alt (TextField): The alternative nucleotide.
        start (BigIntegerField): The starting position of the mutation in ref(couting is 0 based).
        end (BigIntegerField): The ending position of the mutation in ref.
        alignments (ManyToManyField): Many-to-many relationship with Alignment (representing samples) instances.

    Constraints:
        - Ensures that the combination of `ref`, `alt`, `start`, `end`, and `replicon`
          is unique for each mutation in the replicon.
    """

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
    """
    Represents an amino acid mutation, storing information about the mutation's
    position in ref, the reference and alternative amino acids,
    and links to nucleotide mutations resulting in cds mutation.
    Alignments represent samples with this cds mutation

    Attributes:
        cds (ForeignKey): The coding sequence in which the mutation is located.
        ref (TextField): The reference amino acid
        alt (TextField): The alternative amino acid/ the mutation
        start (BigIntegerField): The start position of the mutation in ref.
        end (BigIntegerField): The end position of the mutation in ref.
        parent (ManyToManyField): Many-to-many relationship with nucleotide mutations (multiple mutations can result in one amino acid mutation).
        alignments (ManyToManyField): Many-to-many relationship with alignments (samples) containing this mutation.

    Constraints:
        - Ensures that the combination of `ref`, `alt`, `start`, `end`, `cds`, and `replicon`
          is unique for each mutation in the replicon and CDS.
    """

    cds = models.ForeignKey(CDS, models.CASCADE)
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
            models.Index(fields=["cds"]),
            models.Index(fields=["start"]),
            models.Index(fields=["end"]),
            models.Index(fields=["ref"]),
            models.Index(fields=["alt"]),
        ]
        constraints = [
            UniqueConstraint(
                name="unique_aa_mutation",
                fields=["ref", "alt", "start", "end", "cds", "replicon"],
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
