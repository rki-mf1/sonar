import calendar
from datetime import datetime
import os
import pathlib

from Bio import SeqFeature
from Bio import SeqIO
from Bio import SeqRecord
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction

from covsonar_backend.settings import SONAR_DATA_ENTRY_FOLDER
from rest_api.models import CDS
from rest_api.models import CDSSegment
from rest_api.models import Gene
from rest_api.models import GeneSegment
from rest_api.models import Peptide
from rest_api.models import PeptideSegment
from rest_api.models import Reference
from rest_api.models import Replicon
from rest_api.serializers import CDSSegmentSerializer
from rest_api.serializers import CDSSerializer
from rest_api.serializers import find_or_create
from rest_api.serializers import GeneSegmentSerializer
from rest_api.serializers import GeneSerializer
from rest_api.serializers import PeptideSegmentSerializer
from rest_api.serializers import PeptideSerializer
from rest_api.serializers import ReferenceSerializer
from rest_api.serializers import RepliconSerializer


def import_gbk_file(uploaded_files: list[InMemoryUploadedFile], translation_id: int):
    """
    Import GenBank file. or Import multiple GenBank files as segments.

    Args:
        - uploaded_files (list): List of InMemoryUploadedFile objects.
        - translation_id (int): ID for translation.
    """
    records = []
    file_paths = []
    for uploaded_file in uploaded_files:
        file_path = _temp_save_file(uploaded_file)
        file_paths.append(str(file_path))
        records.extend(list(SeqIO.parse(file_path, "genbank")))

    file_path_str = ", ".join(
        file_paths
    )  # join multiple file paths into a comma-space separated string
    records: list[SeqRecord.SeqRecord]
    reference = _put_reference_from_record(records[0], translation_id, file_path_str)
    with transaction.atomic():
        # record = complete gbk file
        for record in records:
            source_features = list(
                filter(lambda x: x.type == "source", record.features)
            )
            if len(source_features) != 1:
                raise ValueError("Expecting exactly one source feature.")
            source_feature = source_features[0]
            source_feature: SeqFeature.SeqFeature
            if source_feature.location is None:
                raise ValueError("No location information found for source feature.")
            replicon_data = {
                "accession": f"{record.name}.{record.annotations['sequence_version']}",
                "description": record.description,
                "length": int(source_feature.location.end)
                - int(source_feature.location.start),
                "sequence": str(source_feature.extract(record.seq)),
                "reference": reference.id,
            }
            # If the record has a segment number at the top level, use that
            # else look at the source feature for segment number
            if "segment_number" in record.annotations:
                replicon_data["segment_number"] = record.annotations["segment_number"]
            else:
                source_features = [f for f in record.features if f.type == "source"]

                if (
                    len(source_features) == 1
                    and "segment" in source_features[0].qualifiers
                ):
                    replicon_data["segment_number"] = source_features[0].qualifiers[
                        "segment"
                    ][0]

            replicon = find_or_create(replicon_data, Replicon, RepliconSerializer)
            # features with gene qualifier
            gene_features = [
                f
                for f in record.features
                if f.type == "gene" and "pseudogene" not in f.qualifiers
            ]
            none_gene_features = [
                f
                for f in record.features
                if f.type != "gene" and "pseudogene" not in f.qualifiers
            ]

            gene_id_to_gene_obj: dict[str, Gene] = {}
            for gene_feature in gene_features:
                """
                gene_feature = type: gene, location: [26244:26472](+), qualifiers: Key: gene, Value: ['E']
                """
                gene_symbol = (
                    gene_feature.qualifiers.get("gene", [None])[0]
                    or gene_feature.qualifiers.get("locus_tag", [None])[0]
                )
                if gene_symbol is None:
                    raise ValueError(
                        f"No gene symbol found for feature at {gene_feature.location}."
                    )

                gene_type = determine_gene_type(none_gene_features, gene_symbol)
                # TODO : check if join/multiple orders
                gene_obj = _put_gene_from_feature(
                    gene_feature, record.seq, replicon, gene_type
                )
                gene_id_to_gene_obj[gene_symbol] = gene_obj
                _create_gene_segments(gene_feature, gene_obj)

            # features with CDS qualifier
            gene_id_to_cds_obj: dict[str, list[CDS]] = {}
            cds_features = [
                f
                for f in record.features
                if f.type == "CDS" and "pseudogene" not in f.qualifiers
            ]
            for cds_feature in cds_features:
                # TODO add note to cds table (e.g. ORF1)
                gene_symbol = (
                    cds_feature.qualifiers.get("gene", [None])[0]
                    or cds_feature.qualifiers.get("locus_tag", [None])[0]
                )
                if gene_symbol is None:
                    raise ValueError(
                        f"No gene symbol found for CDS feature at {cds_feature.location}."
                    )
                gene = gene_id_to_gene_obj.get(gene_symbol, None)
                if gene is None:
                    raise ValueError("No gene object found for CDS.")
                cds = _put_cds_from_feature(cds_feature, gene)
                # different cds in one gene
                if gene_symbol not in gene_id_to_cds_obj:
                    gene_id_to_cds_obj[gene_symbol] = []
                    gene_id_to_cds_obj[gene_symbol].append(cds)
                else:
                    gene_id_to_cds_obj[gene_symbol].append(cds)
                _create_cds_segments(cds_feature, cds)

            # features with peptide qualifier (e.g. HIV)
            peptide_features = [
                f for f in record.features if f.type in ["mat_peptide", "sig_peptide"]
            ]
            for peptide_feature in peptide_features:
                gene_symbol = (
                    peptide_feature.qualifiers.get("gene", [None])[0]
                    or peptide_feature.qualifiers.get("locus_tag", [None])[0]
                )
                if gene_symbol is None:
                    raise ValueError("No gene symbol found for peptide feature.")
                cds_objects = gene_id_to_cds_obj.get(gene_symbol, None)
                cds_segments = CDSSegment.objects.filter(
                    cds__in=[cds.pk for cds in cds_objects]
                )
                if cds is None:
                    raise ValueError("No gene found for peptide.")
                elif len(cds_objects) > 1:
                    raise ValueError(
                        f"Multiple CDS objects found for gene symbol {gene_symbol}. Can't assign mat_peptides to CDS."
                    )
                elif len(cds_objects) == 1:
                    cds = cds_objects[0]
                    peptide = _put_peptide_from_feature(peptide_feature, cds)
                    _create_peptide_segments(peptide_feature, peptide, cds_segments)

    return records


def determine_gene_type(
    none_gene_features: list[SeqFeature.SeqFeature], gene_symbol: str
) -> Gene.GeneTypes | None:
    types = [
        Gene.GeneTypes(feature.type)
        for feature in none_gene_features
        if feature.type in Gene.GeneTypes.values
        and feature.qualifiers.get("gene", [None])[0] == gene_symbol
    ]
    if len(set(types)) > 1:
        raise ValueError(f"Multiple gene types found for {gene_symbol}: {types}")
    return types[0] if types else None


def _process_segments(
    feat_location_parts: list[SeqFeature.FeatureLocation | SeqFeature.CompoundLocation],
    include_strand: bool = False,
) -> list[dict[str, int]]:
    """
    Process the genomic regions (segments) of a feature.

    Args:
        feat_location_parts (List[Union[FeatureLocation, CompoundLocation]]): List of feature location parts.
        cds (bool): A flag indicating whether the segment corresponds to a coding sequence.
                    Default is False.

    Returns:
        segments (List[List[int]]): A list of processed segments. Each segment is represented
                                    as a list of integers [start, end, strand, index].
    """
    segments = []
    for i, segment in enumerate(feat_location_parts, 1):
        segment_data = {
            "start": int(segment.start),
            "end": int(segment.end),
            "order": i,
        }
        if include_strand:
            segment_data["forward_strand"] = True if segment.strand == 1 else False
        segments.append(segment_data)
    return segments


def _validate_segment_lengths(parts, accession):
    parts = _process_segments(parts, include_strand=True)
    if sum([abs(x["end"] - x["start"]) for x in parts]) % 3 != 0:
        raise ValueError(f"The length of cds '{accession}' is not a multiple of 3.")


def _determine_accession(feature: SeqFeature.SeqFeature) -> str | None:
    if feature.id != "<unknown id>":
        return feature.id
    elif "gene" in feature.qualifiers and feature.type == "gene":
        return feature.qualifiers["gene"][0]
    elif "protein_id" in feature.qualifiers and feature.type == "CDS":
        return feature.qualifiers["protein_id"][0]
    elif "locus_tag" in feature.qualifiers:
        return feature.qualifiers["locus_tag"][0]
    raise ValueError("No qualifier for gene accession found.")


def _determine_symbol(feature: SeqFeature.SeqFeature) -> str | None:
    if "gene" in feature.qualifiers:
        return feature.qualifiers["gene"][0]
    elif "locus_tag" in feature.qualifiers:
        return feature.qualifiers["locus_tag"][0]
    raise ValueError("No qualifier for gene symbol found.")


def _put_gene_from_feature(
    feature: SeqFeature.SeqFeature,
    replicon_seq: str,
    replicon: Replicon,
    gene_type: Gene.GeneTypes,
) -> Gene:
    """
    Processes a gene feature from a gene bank file and updates or creates a corresponding Gene object.

    Args:
        feature (SeqFeature.SeqFeature): The gene feature containing location and qualifiers.
            e.g. type: gene, location: [26244:26472](+), qualifiers: Key: gene, Value: ['E']
        replicon_seq (str): The full nucleotide sequence of the replicon.
        replicon (Replicon): The associated Replicon object.
        gene_type (Gene.GeneTypes): The type of gene (e.g. CDS, rRNA, etc.).

    Returns:
        Gene: The updated or newly created Gene object.
        gene_accession: filled with first existing tag in this order [gene, protein_id, locus_tag]
        gene_symbol: filled with first existing tag in this order [gene, locus_tag]
        gene_sequence: complete sequence of gene
        gene_locus_tag: locus_tag = systematic gene name
        gene_description: gene_synonym

    Raises:
        ValueError: If the feature has no location information.
    """
    if feature.location is None:
        raise ValueError("No location information found for gene feature.")
    gene_base_data = {
        "start": int(feature.location.start),
        "end": int(feature.location.end),
        "forward_strand": True if feature.location.strand == 1 else False,
        "replicon": replicon.pk,
        "type": gene_type,
    }
    gene_update_data = {}
    gene_update_data["accession"] = _determine_accession(feature)
    gene_update_data["symbol"] = _determine_symbol(feature)
    gene_update_data["sequence"] = str(feature.extract(replicon_seq))
    gene_update_data["locus_tag"] = feature.qualifiers.get("locus_tag", [""])[0]
    gene_update_data["description"] = feature.qualifiers.get("gene_synonym", [""])[0]

    gene = find_or_create(gene_base_data, Gene, GeneSerializer)
    for attr_name, value in gene_update_data.items():
        setattr(gene, attr_name, value)
    return GeneSerializer(gene).update(gene, gene_update_data)


def _put_cds_from_feature(feature: SeqFeature.SeqFeature, gene: Gene) -> CDS:
    """
    Processes a cds feature from a gene bank file and updates or creates a corresponding CDS object.
    Location information stored in related cds_segment table

    Args:
        feature (SeqFeature.SeqFeature): The cds feature containing location and qualifiers.
        gene (Gene): The associated gene object.

    Returns:
        CDS: The updated or newly created CDS object.
        cds_accession: filled with first existing tag in this order [gene, protein_id, locus_tag]
        cds_sequence: complete aa-sequence of cds
        cds_descritption: product tag = protein name

    Raises:
        ValueError: If the feature has no location information.
    """
    if feature.location is None:
        raise ValueError("No location information found for CDS feature.")
    cds_update_data = {}
    cds_update_data["accession"] = _determine_accession(feature)
    _validate_segment_lengths(feature.location.parts, cds_update_data["accession"])
    cds_update_data["sequence"] = feature.qualifiers.get("translation", [""])[0]
    cds_update_data["description"] = feature.qualifiers.get("product", [""])[0]
    cds = find_or_create(
        {"gene": gene.pk, "accession": cds_update_data["accession"]}, CDS, CDSSerializer
    )
    for attr_name, value in cds_update_data.items():
        setattr(cds, attr_name, value)
    return CDSSerializer(cds).update(cds, cds_update_data)


def _put_peptide_from_feature(feature: SeqFeature.SeqFeature, cds: CDS) -> Peptide:
    """
    Processes a peptide feature from a gene bank file and updates or creates a corresponding Peptide object.
    Location information stored in related peptide_segment table

    Args:
        feature (SeqFeature.SeqFeature): The cds feature containing location and qualifiers.
        cds (CDS): The associated CDS object.

    Returns:
        Peptide: The updated or newly created peptide object.
        peptide_type: mat_peptide or sig_peptide
        peptide_descritption: product tag = protein name

    Raises:
        ValueError: If the feature has no location information.
    """
    if feature.location is None:
        raise ValueError("No location information found for peptide feature.")
    peptide_base_data = {
        "cds": cds.pk,
        "type": feature.type,
        "description": feature.qualifiers.get("product", [""])[0],
    }
    peptide_update_data = {}
    peptide = find_or_create(peptide_base_data, Peptide, PeptideSerializer)
    for attr_name, value in peptide_update_data.items():
        setattr(peptide, attr_name, value)
    return PeptideSerializer(peptide).update(peptide, peptide_update_data)


def parse_date(date_string: str) -> datetime.date:
    date_formats = ["%Y-%m", "%d-%b-%Y", "%Y", "%Y-%m-%d", "%Y-%b-%d"]
    for date_format in date_formats:
        try:
            return datetime.strptime(date_string, date_format).date()
        except ValueError:
            continue
    # Handle custom format "Dec-2019" without relying on locale (problems can occur in some settings)
    try:
        month_str, year = date_string.split("-")
        month = list(calendar.month_abbr).index(month_str[:3])
        return datetime(year=int(year), month=month, day=1).date()
    except (ValueError, IndexError):
        pass

    raise ValueError(f"Date string '{date_string}' does not match any known formats.")


def _put_reference_from_record(
    record: SeqRecord.SeqRecord, translation_id: int, file_path: str
) -> Reference:
    source = None
    for feature in record.features:
        if feature.type == "source":
            source = feature
            break
    if source is None:
        raise Exception("No source feature found.")
    if "db_xref" in source.qualifiers:
        if ref := Reference.objects.filter(
            db_xref=source.qualifiers["db_xref"]
        ).first():
            return ref
    reference = {
        "accession": f"{record.name}.{record.annotations['sequence_version']}",
        "description": record.description,
        "organism": record.annotations["organism"],
        "translation_id": translation_id,
        "name": str(file_path),
    }
    for attr_name in [
        "mol_type",
        "isolate",
        "host",
        "db_xref",
        "country",
        "collection_date",
    ]:
        if attr_name in source.qualifiers:
            if attr_name == "collection_date":
                date_string = source.qualifiers[attr_name][0]
                reference[attr_name] = parse_date(date_string).strftime("%Y-%m-%d")
            else:
                reference[attr_name] = source.qualifiers[attr_name][0]
        else:
            reference[attr_name] = None
    try:
        return Reference.objects.get(db_xref=reference["db_xref"])
    except Reference.DoesNotExist:
        serializer = ReferenceSerializer(data=reference)
        serializer.is_valid(raise_exception=True)
        return serializer.save()


def _create_gene_segments(feature: SeqFeature.SeqFeature, gene: Gene):
    for elempart in _process_segments(feature.location.parts, include_strand=True):
        elempart_data = {
            "gene": gene.pk,
            **elempart,
        }
        find_or_create(elempart_data, GeneSegment, GeneSegmentSerializer)


def _create_cds_segments(feature: SeqFeature.SeqFeature, cds: CDS):
    for elempart in _process_segments(feature.location.parts, include_strand=True):
        elempart_data = {
            "cds": cds.pk,
            **elempart,
        }
        find_or_create(elempart_data, CDSSegment, CDSSegmentSerializer)


def calculate_cds_start_end(
    seq_feature: SeqFeature.SeqFeature,
    cds_segments: list[CDSSegment],
    cds_accession: str | None = None,
) -> tuple[int, int]:
    """
    Calculate the start and end positions of a peptide segment in relation to the CDS amino acid sequence.

    Args:
        seq_feature (SeqFeature.SeqFeature): The peptide feature with location information.
        cds_segments (list[CDSSegment]): List of CDS segments (start, end, strand, order).

    Returns:
        tuple[int, int]: Start and end positions of the peptide in the CDS amino acid sequence.
    """
    # Flatten the CDS segments into a continuous nucleotide position list
    cds_nt_positions = []
    for segment in cds_segments:
        if segment.forward_strand:
            cds_nt_positions.extend(range(segment.start, segment.end + 1))
        else:
            cds_nt_positions.extend(range(segment.end, segment.start - 1, -1))

    # Map peptide segment positions to CDS nucleotide positions
    peptide_start_nt = int(seq_feature.location.start)
    peptide_end_nt = int(seq_feature.location.end)

    # Find the peptide's start and end positions in the CDS nucleotide sequence
    try:
        start_cds_nt = cds_nt_positions.index(peptide_start_nt) + 1
        end_cds_nt = cds_nt_positions.index(peptide_end_nt) + 1
    except ValueError:
        raise ValueError("Peptide segment is not part of the CDS segments.")

    # Convert nucleotide positions to amino acid positions
    start_cds_aa = (start_cds_nt + 2) // 3  # Convert to 1-based AA position
    end_cds_aa = (end_cds_nt + 2) // 3  # Convert to 1-based AA position
    if start_cds_aa < 0 or end_cds_aa < 0:
        raise ValueError(
            f"Start or end cds position of peptide segment is out of range for CDS {cds_accession}."
        )
    if start_cds_aa == end_cds_aa:
        raise ValueError(
            f"Start and end position (start_cds, end_cds) of peptide segment are equal for CDS {cds_accession}."
        )
    return start_cds_aa, end_cds_aa


def _create_peptide_segments(
    seq_feature: SeqFeature.SeqFeature, peptide, cds_segments: list[CDSSegment]
):
    """
    Create peptide segments based on the provided sequence feature and peptide object.
    Args:
        seq_feature (SeqFeature.SeqFeature): The sequence feature containing location information.
        peptide (Peptide): The associated peptide object.
        cds_segments (list[CDSSegment]): List of CDS segments (start, end, strand, order) of associated CDS
    """
    for elempart in _process_segments(seq_feature.location.parts):
        start_cds_aa, end_cds_aa = calculate_cds_start_end(
            seq_feature,
            cds_segments,
            peptide.cds.accession,
        )
        elempart_data = {
            "peptide": peptide.pk,
            "start_cds": start_cds_aa,
            "end_cds": end_cds_aa,
            **elempart,
        }
        find_or_create(elempart_data, PeptideSegment, PeptideSegmentSerializer)


def _temp_save_file(uploaded_file: InMemoryUploadedFile):
    # Create the directory path
    directory_path = pathlib.Path(SONAR_DATA_ENTRY_FOLDER) / "gbks"
    directory_path.mkdir(exist_ok=True)
    file_path = directory_path / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())
    return file_path
