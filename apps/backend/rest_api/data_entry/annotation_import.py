from dataclasses import dataclass
import re

from django.db.models import Q

from covsonar_backend.settings import LOGGER
from rest_api.models import AnnotationType
from rest_api.models import Mutation


@dataclass
class VCFRaw:
    chrom: str  # mutation__replicon__accession
    pos: int  # mutation__start
    id: str
    ref: str  # mutation__ref
    alt: str | None
    qual: str
    filter: str
    info: str
    format: str


@dataclass
class VCFInfoANNRaw:
    # Functional annotations
    allele: str
    annotation: str
    annotation_impact: str
    gene_name: str
    gene_id: str
    feature_type: str
    feature_id: str
    transcript_bio_type: str
    rank: str
    hgvs_c: str
    hgvs_p: str
    c_dna_pos_length: str
    cds_pos_length: str
    aa_pos_length: str
    distance: str
    errors_warnings_info: str


@dataclass
class MutationLookupToAnnotations:
    start: str
    end: str
    ref: str
    alt: str
    replicon__accession: str
    annotations: list[VCFInfoANNRaw]


class AnnotationImport:
    def __init__(self, path: str):
        self.vcf_file_path = path
        self.raw_lines = [line for line in self._import_vcf()]
        self.mutation_lookups_to_annotations = self.convert_lines()
        self.annotation_q_obj = Q()

    def _import_vcf(self):
        with open(self.vcf_file_path, "r") as handle:
            for line in handle:
                if line.startswith(("#", "##")):
                    continue
                line = line.strip("\r\n").split("\t")
                vcf_raw = VCFRaw(
                    chrom=line.pop(0),
                    pos=int(line.pop(0)),
                    id=line.pop(0),
                    ref=line.pop(0),
                    alt=None if (alt := line.pop(0)) == "." else alt,
                    qual=line.pop(0),
                    filter=line.pop(0),
                    info=line.pop(0),
                    format=line.pop(0),
                )
                yield vcf_raw

    def convert_lines(self) -> list[MutationLookupToAnnotations]:
        mutation_lookups_to_annotations = []
        for line in self.raw_lines:
            annotations = self._parse_line_info(line.info)
            allele_to_annotations = {}
            for annotation in annotations:
                if annotation.allele not in allele_to_annotations:
                    allele_to_annotations[annotation.allele] = []
                allele_to_annotations[annotation.allele].append(annotation)
            for alt in line.alt.split(","):
                if alt not in allele_to_annotations:
                    continue
                mutation_lookup_to_annotations = MutationLookupToAnnotations(
                    start=line.pos
                    - 1,  # snp (we deduct by one because our database use 0-based)
                    end=int(line.pos),
                    ref=line.ref,
                    alt=alt,
                    replicon__accession=line.chrom,
                    annotations=allele_to_annotations[alt],
                )
                if len(alt) < len(mutation_lookup_to_annotations.ref):
                    # deletion and alt not null
                    # because in vcf it always show the positon before deletion
                    # for example; MN908947.3	506	.	CATGGTCATGTTATGGTTG	C
                    mutation_lookup_to_annotations.start += 1
                    mutation_lookup_to_annotations.end = (
                        mutation_lookup_to_annotations.end
                        + len(mutation_lookup_to_annotations.ref)
                        - 1
                    )
                    # add None here if we dont want to keep the deletion in ref
                    # column, however the program frozen once I change to
                    # mutation_lookup_to_annotations.ref = None
                    mutation_lookup_to_annotations.ref = ""
                    mutation_lookup_to_annotations.alt = None

                mutation_lookups_to_annotations.append(mutation_lookup_to_annotations)
        return mutation_lookups_to_annotations

    def _parse_line_info(self, info: str) -> list[VCFInfoANNRaw]:
        """
        Extracts the SNP effect annotation (ANN) substring from the 8th column of a tab-separated SnpEff annotation line.

        Parameters:
            info (str): The 8th column of a tab-separated SnpEff annotation line. Example:
                "ANN=C|upstream_gene_variant|MODIFIER|ORF1a|Gene_265_13467|transcript|ORF1a|protein_coding||c.-217_-213delTCTTG|||||217|WARNING_TRANSCRIPT_NO_STOP_CODON,
                C|intergenic_region|MODIFIER|CHR_START-ORF1a|CHR_START-Gene_265_13467|intergenic_region|CHR_START-Gene_265_13467|||n.49_53delTCTTG||||||"

        Returns:
            list[VCFInfoANNRaw]: list of extracted annotations, different annotations are separated by ','
        """
        for field in info.split(";"):
            if field.startswith("ANN="):
                ann_field = field.removeprefix("ANN=")
                annotations = []
                for annotation in ann_field.split(","):
                    annotation = annotation.split("|")
                    try:
                        annotations.append(VCFInfoANNRaw(*annotation))
                    except Exception:
                        LOGGER.warning(
                            f"Failed to parse annotation: {annotation}, from file {self.vcf_file_path}"
                        )
                # Return after finding the first ANN= field. If there are
                # multiple, all others will be ignored.
                return annotations
        return None

    def get_annotation_objs(
        self,
    ) -> tuple[list[AnnotationType], list[AnnotationType.mutations.through]]:
        annotation_objs = []
        q_obj = Q()
        # self.mutation_lookups_to_annotations read from vcf file.
        for mutation_lookup_to_annotations in self.mutation_lookups_to_annotations:
            q_obj |= Q(
                start=mutation_lookup_to_annotations.start,
                end=mutation_lookup_to_annotations.end,
                ref=mutation_lookup_to_annotations.ref,
                alt=mutation_lookup_to_annotations.alt,
                replicon__accession=mutation_lookup_to_annotations.replicon__accession,
                type="nt",
            )
        mutations = Mutation.objects.filter(q_obj).prefetch_related("replicon")
        annotation_q_obj = Q()
        relation_info = {}
        for mutation in mutations:
            # Problem 1: some samples got error 'StopIteration'
            # I think because there are no items in the filtered iterable
            # that match the conditions specified by the lambda function
            # But How did this can happen?,
            # Solution: because there are cds and nt at the same position we should filter only NT

            try:
                mut_lookup_to_annotation = self.mutation_lookups_to_annotations.pop(
                    self.mutation_lookups_to_annotations.index(
                        next(
                            filter(
                                lambda x: int(x.start) == int(mutation.start)
                                and int(x.end) == int(mutation.end)
                                and x.ref == mutation.ref
                                and x.alt == mutation.alt
                                and x.replicon__accession
                                == mutation.replicon.accession,
                                self.mutation_lookups_to_annotations,
                            )
                        )
                    )
                )
            except (ValueError, StopIteration) as e:
                LOGGER.error(f"Error: {e}")
                LOGGER.error(
                    f"Mutation details: start={mutation.start}, end={mutation.end}, ref={mutation.ref}, alt={mutation.alt}, replicon__accession={mutation.replicon.accession}"
                )
                raise

            # print(mut_lookup_to_annotation)
            # Problem 2: We have too many entries in mut_lookup_to_annotation.annotations.
            # For example, if we have the mutation MN908947.3 26565 . A ANNNNNNN (insertion with ambiguous lots of Ns),
            # snpEff tries to predict the effect for every possible combination:
            # insCAAAAAA, insCAAAAAC, insCAAAAAG, insCAAAAAT, ..., insTAAAAAA, ..., insGAAAAAA.
            # This can generate a lookup annotation size of 4 (A,T,C,G) to the power of N (position).
            # In this case, 4 to the power of 7 equals 16384.
            # Currently, we only use ontology (e.g., frameshift_variant) and annotation_impact (e.g., HIGH),
            # which means a potentially highly redundant query, hence taking too long to finish the import process (> 10 mins).

            # Temporary solution: reduce the redundancy in alleles, annotations, and impacts.
            # we skip processing based on alleles, annotations, and impacts
            seen = set()
            # start to pass each VCFInfoANNRaw
            for a in mut_lookup_to_annotation.annotations:
                key = (a.allele, a.annotation, a.annotation_impact)
                if key in seen:
                    continue
                seen.add(key)
                for ontology in a.annotation.split("&"):
                    annotation_obj = AnnotationType(
                        seq_ontology=ontology, impact=a.annotation_impact
                    )
                    annotation_q_obj |= Q(
                        seq_ontology=ontology, impact=a.annotation_impact
                    )
                    if ontology not in relation_info:
                        relation_info[ontology] = {}
                    if a.annotation_impact not in relation_info[ontology]:
                        relation_info[ontology][a.annotation_impact] = []
                    relation_info[ontology][a.annotation_impact].append(
                        {
                            "mutation": mutation,
                        }
                    )
                    annotation_objs.append(annotation_obj)
        self.annotation_q_obj = annotation_q_obj
        self.relation_info = relation_info
        return annotation_objs

    def get_annotation2mutation_objs(self) -> list[AnnotationType.mutations.through]:
        annotations = AnnotationType.objects.filter(self.annotation_q_obj)
        mutation2annotation_objs = []
        for annotation in annotations:
            for relation in self.relation_info[annotation.seq_ontology][
                annotation.impact
            ]:
                mutation = relation["mutation"]
                mutation2annotation_objs.append(
                    AnnotationType.mutations.through(
                        annotationtype_id=annotation.id,
                        mutation_id=mutation.id,
                    )
                )
        return mutation2annotation_objs
