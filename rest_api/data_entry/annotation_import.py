from dataclasses import dataclass
from rest_api.models import (
    Mutation,
    AnnotationType,
    Alignment,
    Mutation2Annotation,
    Sample,
    Sequence,
)
from django.db.models import Q
import re


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
    samples: dict[str, str] = None


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
    ref: str
    alt: str
    replicon__accession: str
    annotations: list[VCFInfoANNRaw]
    samples: list[str]


class AnnotationImport:
    def __init__(self, path: str):
        self.vcf_file_path = path
        self.sample_to_sequence = {}
        self.replicon_to_sample_to_alignment = {}
        self.raw_lines = [line for line in self._import_vcf()]
        self.fetch_sequences()
        self.fetch_alignments()
        self.mutation_lookups_to_annotations = self.convert_lines()

    def _import_vcf(self):
        with open(self.vcf_file_path, "r") as handle:
            for line in handle:
                if line.startswith("##"):
                    continue
                if line.startswith("#"):
                    self.samples = line.strip("\r\n").split("\t")[9:]
                    continue
                elif self.samples is None:
                    raise ValueError(
                        "Annoation file in unexpected format. Missing header."
                    )
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
                vcf_raw.samples = {self.samples[i]: line[i] for i in range(len(line))}
                if vcf_raw.chrom not in self.replicon_to_sample_to_alignment:
                    self.replicon_to_sample_to_alignment[vcf_raw.chrom] = {}
                for sample in self.samples:
                    self.replicon_to_sample_to_alignment[vcf_raw.chrom][sample] = None
                yield vcf_raw

    def fetch_sequences(self):
        q_obj = Q()
        for sample in self.samples:
            q_obj |= Q(name=sample)
        self.sample_to_sequence = {}
        for sample in Sample.objects.filter(q_obj).prefetch_related("sequence"):
            try:
                self.sample_to_sequence[sample.name] = sample.sequence
            except KeyError:
                continue                
                

    def fetch_alignments(self):
        q_obj = Q()
        for replicon in self.replicon_to_sample_to_alignment.keys():
            for sample in self.replicon_to_sample_to_alignment[replicon]:
                try:
                    q_obj |= Q(
                        sequence=self.sample_to_sequence[sample],
                        replicon__accession=replicon,
                    )
                except KeyError:
                    continue  
        alignments = Alignment.objects.filter(q_obj).prefetch_related(
            "sequence__sample_set"
        )
        for alignment in alignments:
            for sample in alignment.sequence.sample_set.all():
                self.replicon_to_sample_to_alignment[alignment.replicon.accession][
                    sample.name
                ] = alignment

    def convert_lines(self) -> list[MutationLookupToAnnotations]:
        mutation_lookups_to_annotations = []
        for line in self.raw_lines:
            annotations = self._parse_line_info(line.info)
            allele_to_annotations = {}
            for annotation in annotations:
                if annotation.allele not in allele_to_annotations:
                    allele_to_annotations[annotation.allele] = []
                allele_to_annotations[annotation.allele].append(annotation)
            sample_index = 0
            for alt in line.alt.split(","):
                sample_index += 1
                if alt not in allele_to_annotations:
                    continue
                samples = []
                for sample, occurence in line.samples.items():
                    if occurence == f"0/{sample_index}":
                        samples.append(sample)
                mutation_lookup_to_annotations = MutationLookupToAnnotations(
                    start=line.pos - 1,
                    ref=line.ref,
                    alt=alt,
                    replicon__accession=line.chrom,
                    annotations=allele_to_annotations[alt],
                    samples=samples,
                )
                if alt and len(alt) < len(mutation_lookup_to_annotations.ref):
                    # deletion and alt not null
                    mutation_lookup_to_annotations.start += 1
                    mutation_lookup_to_annotations.ref = (
                        mutation_lookup_to_annotations.ref[1:]
                    )
                    mutation_lookup_to_annotations.alt = None
                mutation_lookups_to_annotations.append(mutation_lookup_to_annotations)
        return mutation_lookups_to_annotations

    def _parse_line_info(self, info: str) -> list[VCFInfoANNRaw]:
        # only ANN= is parsed
        if info.startswith("ANN="):
            r = re.compile(r"\(([^()]*|(R))*\)")
            info = info[4:]
            annotations = []
            for annotation in info.split(","):
                # replace pipes inside paranthesis
                annotation = r.sub(lambda x: x.group().replace("|", "-"), annotation)
                annotation = annotation.split("|")
                try:
                    annotations.append(VCFInfoANNRaw(*annotation))
                except Exception:
                    print(
                        f"Failed to parse annotation: {annotation}, from file {self.vcf_file_path}"
                    )

            return annotations
        return None

    def get_annotation_objs(
        self,
    ) -> tuple[list[AnnotationType], list[Mutation2Annotation]]:
        annotation_objs = []
        q_obj = Q()
        for mutation_lookup_to_annotations in self.mutation_lookups_to_annotations:
            q_obj |= Q(
                start=mutation_lookup_to_annotations.start,
                ref=mutation_lookup_to_annotations.ref,
                alt=mutation_lookup_to_annotations.alt,
                replicon__accession=mutation_lookup_to_annotations.replicon__accession,
            )
        mutations = Mutation.objects.filter(q_obj).prefetch_related("replicon")
        annotation_q_obj = Q()
        relation_info = {}
        for mutation in mutations:
            mut_lookup_to_annotation = self.mutation_lookups_to_annotations.pop(
                self.mutation_lookups_to_annotations.index(
                    next(
                        filter(
                            lambda x: x.start == mutation.start
                            and x.ref == mutation.ref
                            and x.alt == mutation.alt
                            and x.replicon__accession == mutation.replicon.accession,
                            self.mutation_lookups_to_annotations,
                        )
                    )
                )
            )
            for a in mut_lookup_to_annotation.annotations:
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
                    for sample in mut_lookup_to_annotation.samples:
                        relation_info[ontology][a.annotation_impact].append(
                            {
                                "mutation": mutation,
                                "alignment": self.replicon_to_sample_to_alignment[
                                    mut_lookup_to_annotation.replicon__accession
                                ][sample],
                            }
                        )
                    annotation_objs.append(annotation_obj)
        self.annotation_q_obj = annotation_q_obj
        self.relation_info = relation_info
        return annotation_objs

    def get_annotation2mutation_objs(self) -> list[Mutation2Annotation]:
        annotations = AnnotationType.objects.filter(self.annotation_q_obj)
        mutation2annotation_objs = []
        for annotation in annotations:
            for relation in self.relation_info[annotation.seq_ontology][
                annotation.impact
            ]:
                mutation = relation["mutation"]
                alignment = relation["alignment"]
                if alignment:
                    mutation2annotation_objs.append(
                        Mutation2Annotation(
                            annotation=annotation,
                            mutation=mutation,
                            alignment=alignment,
                        )
                    )
        return mutation2annotation_objs
