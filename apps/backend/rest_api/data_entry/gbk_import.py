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


def import_gbk_file(uploaded_file: InMemoryUploadedFile, translation_id: int):
    file_path = _temp_save_file(uploaded_file)
    records = list(SeqIO.parse(file_path, "genbank"))
    records: list[SeqRecord.SeqRecord]
    reference = _put_reference_from_record(records[0], translation_id, file_path)
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
            if "segment_number" in record.annotations:
                replicon_data["segment_number"] = record.annotations[
                    "segment_number"
                ]  # TODO ?? id
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
                gene_symbol = gene_feature.qualifiers.get("gene", [None])[0]
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
            gene_id_to_cds_obj: dict[str, list(CDS)] = {}
            cds_features = [
                f
                for f in record.features
                if f.type == "CDS" and "pseudogene" not in f.qualifiers
            ]
            for cds_feature in cds_features:
                # TODO add note to cds table (e.g. ORF1)
                gene_symbol = cds_feature.qualifiers.get("gene", [None])[0]
                if gene_symbol is None:
                    raise ValueError("No gene symbol found.")
                # TODO : check if join/multiple orders
                gene = gene_id_to_gene_obj.get(gene_symbol, None)
                if gene is None:
                    raise ValueError("No gene object found for CDS.")
                cds = _put_cds_from_feature(cds_feature, record.seq, gene)
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
                gene_symbol = peptide_feature.qualifiers.get("gene", [None])[0]
                if gene_symbol is None:
                    raise ValueError("No gene symbol found.")
                # TODO : check if join/multiple orders
                cds_objects = gene_id_to_cds_obj.get(gene_symbol, None)
                if cds is None:
                    raise ValueError("No gene found for peptide.")
                elif len(cds_objects) > 1:
                    raise ValueError(
                        f"Multiple CDS objects found for gene symbol {gene_symbol}. Can't assign mat_peptides to CDS."
                    )
                elif len(cds_objects) == 1:
                    cds = cds_objects[0]
                    peptide = _put_peptide_from_feature(
                        peptide_feature, record.seq, cds
                    )
                    _create_peptide_segments(peptide_feature, peptide)

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
    Processes a gene feature from a sequence and updates or creates a corresponding Gene object.

    Args:
        feature (SeqFeature.SeqFeature): The gene feature containing location and qualifiers.
            e.g. type: gene, location: [26244:26472](+), qualifiers: Key: gene, Value: ['E']
        replicon_seq (str): The full nucleotide sequence of the replicon.
        replicon (Replicon): The associated Replicon object.
        gene_type (Gene.GeneTypes): The type of gene (e.g. CDS, rRNA, etc.).

    Returns:
        Gene: The updated or newly created Gene object.

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

    gene = find_or_create(gene_base_data, Gene, GeneSerializer)
    for attr_name, value in gene_update_data.items():
        setattr(gene, attr_name, value)
    return GeneSerializer(gene).update(gene, gene_update_data)


def _put_cds_from_feature(
    feature: SeqFeature.SeqFeature, source_seq: str, gene: Gene
) -> CDS:
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


def _put_peptide_from_feature(
    feature: SeqFeature.SeqFeature, source_seq: str, cds: CDS
) -> Peptide:
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
                # handle both date formats
                date_string = source.qualifiers[attr_name][0]
                try:
                    reference[attr_name] = datetime.strptime(
                        date_string, "%Y-%m"
                    ).date()
                except ValueError:
                    try:
                        reference[attr_name] = datetime.strptime(
                            date_string, "%d-%b-%Y"
                        ).date()
                    except ValueError:
                        reference[attr_name] = datetime.strptime(
                            date_string, "%b-%Y"
                        ).date()
            else:
                reference[attr_name] = source.qualifiers[attr_name][0]
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


def _create_peptide_segments(feature: SeqFeature.SeqFeature, peptide: Peptide):
    for elempart in _process_segments(feature.location.parts):
        elempart_data = {
            "peptide": peptide.pk,
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
