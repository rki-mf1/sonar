from datetime import datetime
import pathlib

from Bio import SeqFeature, SeqIO, SeqRecord
from django.core.files.uploadedfile import InMemoryUploadedFile

from rest_api.models import (
    GeneSegment,
    Replicon,
    Gene,
    Reference,
)
from rest_api.serializers import (
    GeneSerializer,
    RepliconSerializer,
    GeneSegmentSerializer,
    ReferenceSerializer,
    find_or_create,
)

from django.db import transaction


def import_gbk_file(uploaded_file: InMemoryUploadedFile):
    records = list(SeqIO.parse(_temp_save_file(uploaded_file), "genbank"))
    records: list[SeqRecord.SeqRecord]
    reference = _put_reference_from_record(records[0])
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
                "length": int(source_feature.location.end.position)
                - int(source_feature.location.start),
                "sequence": str(source_feature.extract(record.seq)),
                "reference": reference.id,
            }
            if "segment_number" in record.annotations:
                replicon_data["segment_number"] = record.annotations[
                    "segment_number"
                ]  # TODO ?? id
            replicon = find_or_create(replicon_data, Replicon, RepliconSerializer)
            for feature in record.features:
                if "pseudogene" in feature.qualifiers or feature.type not in [
                    "CDS",
                    "gene",
                ]:
                    continue
                element = _put_gene_from_feature(feature, record.seq, replicon.id)
                _create_elemparts(feature, element)
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
    div = 1 if not cds else 3
    segments = []
    for i, segment in enumerate(feat_location_parts, 1):
        segments.append(
            {
                "start": int(segment.start),
                "end": int(segment.end),
                "strand": segment.strand,
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


def _put_gene_from_feature(
    feature: SeqFeature.SeqFeature, source_seq: str, replicon_id: int
) -> Gene:
    if feature.type not in ["gene", "CDS"]:
        raise ValueError(f"The provided feature type({feature.type}) is unknown.")
    if feature.location is None:
        raise ValueError("No location information found for gene feature.")
    type = feature.type.lower()
    gene_base_data = {
        "start": int(feature.location.start),
        "end": int(feature.location.end),
        "strand": feature.strand,
        "replicon": replicon_id,
    }
    gene_update_data = {}

    if accession := _determine_accession(feature):
        gene_update_data[f"{type}_accession"] = accession
    else:
        raise ValueError("No qualifier for gene accession found.")

    if "gene" in feature.qualifiers:
        gene_update_data[f"{type}_symbol"] = feature.qualifiers["gene"][0]
    elif "locus_tag" in feature.qualifiers:
        gene_update_data[f"{type}_symbol"] = feature.qualifiers["locus_tag"][0]
    else:
        raise ValueError("No qualifier for gene symbol found.")

    if feature.type == "CDS":
        _validate_segment_lengths(
            feature.location.parts, gene_update_data["cds_accession"]
        )
        gene_update_data[f"{type}_sequence"] = feature.qualifiers.get(
            "translation", [""]
        )[0]
        gene_update_data["description"] = feature.qualifiers.get("product", [""])[0]
    else:
        gene_update_data[f"{type}_sequence"] = str(feature.extract(source_seq))
    gene = find_or_create(gene_base_data, Gene, GeneSerializer)
    for attr_name, value in gene_update_data.items():
        setattr(gene, attr_name, value)
    return GeneSerializer(gene).update(gene, gene_update_data)


def _put_reference_from_record(record: SeqRecord.SeqRecord) -> Reference:
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
                reference[attr_name] = datetime.strptime(
                    source.qualifiers[attr_name][0],
                    "%b-%Y",
                ).date()
            else:
                reference[attr_name] = source.qualifiers[attr_name][0]
    serializer = ReferenceSerializer(data=reference)
    serializer.is_valid(raise_exception=True)
    return serializer.save()


def _create_elemparts(feature: SeqFeature.SeqFeature, gene: Gene):
    for elempart in _process_segments(feature.location.parts):
        elempart_data = {
            "gene": gene.id,
            **elempart,
        }
        find_or_create(elempart_data, GeneSegment, GeneSegmentSerializer)


def _temp_save_file(uploaded_file: InMemoryUploadedFile):
    file_path = pathlib.Path("import_data") / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())
    return file_path
