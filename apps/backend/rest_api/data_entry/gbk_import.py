import os
import pathlib
from datetime import datetime

from Bio import SeqFeature, SeqIO, SeqRecord
from covsonar_backend.settings import SONAR_DATA_ENTRY_FOLDER
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from rest_api.models import CDS, CDSSegment, Gene, GeneSegment, Reference, Replicon
from rest_api.serializers import (
    CDSSerializer,
    GeneSegmentSerializer,
    GeneSerializer,
    ReferenceSerializer,
    RepliconSerializer,
    find_or_create,
)


def import_gbk_file(uploaded_file: InMemoryUploadedFile, translation_id: int):
    file_path = _temp_save_file(uploaded_file)
    records = list(SeqIO.parse(file_path, "genbank"))
    records: list[SeqRecord.SeqRecord]
    reference = _put_reference_from_record(records[0], translation_id, file_path)
    with transaction.atomic():
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
            gene_features = list(
                filter(
                    lambda x: x.type == "gene" and "pseudogene" not in x.qualifiers,
                    record.features,
                )
            )
            cds_features = list(
                filter(
                    lambda x: x.type == "CDS" and "pseudogene" not in x.qualifiers,
                    record.features,
                )
            )
            gene_id_to_obj: dict[str, Gene] = {}
            for gene_feature in gene_features:
                gene_symbol = gene_feature.qualifiers.get("gene", [None])[0]
                if gene_symbol is None:
                    raise ValueError("No gene symbol found.")
                # TODO : check if join/multiple orders
                element = _put_gene_from_feature(gene_feature, record.seq, replicon)
                gene_id_to_obj[gene_feature.qualifiers.gene] = element
                _create_gene_segments(gene_feature, element)

            for cds_feature in cds_features:
                gene_symbol = cds_feature.qualifiers.get("gene", [None])[0]
                if gene_symbol is None:
                    raise ValueError("No gene symbol found.")
                # TODO : check if join/multiple orders
                gene = gene_id_to_obj.get(gene_symbol, None)
                if gene is None:
                    raise ValueError("No gene found for CDS.")
                element = _put_cds_from_feature(
                    cds_feature, record.seq, replicon.id, gene
                )
                _create_cds_segments(cds_feature, element)

    return records


def _process_segments(
    feat_location_parts: list[SeqFeature.FeatureLocation | SeqFeature.CompoundLocation],
    cds: bool = False,
) -> list[dict[str, int]]:
    """
    Process the genomic regions (segments) of a feature.

    Args:
        feat_location_parts (List[Union[FeatureLocation, CompoundLocation]]): List of feature location parts.
        cds (bool): A flag indicating whether the segment corresponds to a coding sequence.
                    Default is False.

    Returns:
        segments (List[List[int]]): A list of processed segments. Each segment is represented
                                    as a list of integers [start, end, strand, base, index].
    """
    base = 0
    div = 3 if cds else 1
    segments = []
    for i, segment in enumerate(feat_location_parts, 1):
        segments.append(
            {
                "start": int(segment.start),
                "end": int(segment.end),
                "forward_strand": segment.forward_strand,
                "base": base,
                "segment": i,
            }
        )
        base += round(int(segment.end) - int(segment.start - 1) / div, 1)
    return segments


def _validate_segment_lengths(parts, accession):
    parts = _process_segments(parts, cds=True)
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
    feature: SeqFeature.SeqFeature, source_seq: str, replicon: Replicon
) -> Gene:
    if feature.location is None:
        raise ValueError("No location information found for gene feature.")
    gene_base_data = {
        "start": int(feature.location.start),
        "end": int(feature.location.end),
        "forward_strand": feature.location.forward_strand,
        "replicon": replicon,
    }
    gene_update_data = {}
    gene_update_data[f"accession"] = _determine_accession(feature)
    gene_update_data[f"symbol"] = _determine_symbol(feature)
    gene_update_data[f"sequence"] = str(feature.extract(source_seq))

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
    cds_update_data[f"accession"] = _determine_accession(feature)
    _validate_segment_lengths(feature.location.parts, cds_update_data["accession"])
    cds_update_data[f"sequence"] = feature.qualifiers.get("translation", [""])[0]
    cds_update_data["description"] = feature.qualifiers.get("product", [""])[0]

    cds = find_or_create({"gene": gene}, CDS, CDSSerializer)

    for attr_name, value in cds_update_data.items():
        setattr(cds, attr_name, value)
    return CDSSerializer(cds).update(cds, cds_update_data)


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
    for elempart in _process_segments(feature.location.parts):
        elempart_data = {
            "gene": gene,
            **elempart,
        }
        find_or_create(elempart_data, GeneSegment, GeneSegmentSerializer)


def _create_cds_segments(feature: SeqFeature.SeqFeature, cds: CDS):
    for elempart in _process_segments(feature.location.parts, cds=True):
        elempart_data = {
            "cds": cds,
            **elempart,
        }
        find_or_create(elempart_data, CDSSegment, CDSSerializer)


def _temp_save_file(uploaded_file: InMemoryUploadedFile):
    # Create the directory path
    directory_path = pathlib.Path(SONAR_DATA_ENTRY_FOLDER) / "gbks"
    directory_path.mkdir(exist_ok=True)
    file_path = directory_path / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())
    return file_path
