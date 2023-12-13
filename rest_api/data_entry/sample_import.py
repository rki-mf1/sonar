import pathlib
import pickle
import re
import typing
from dataclasses import dataclass
from typing import Any

from django.db.models import Q

if typing.TYPE_CHECKING:
    from django.db.models.query import ValuesQuerySet

from rest_api.models import (
    Alignment,
    AnnotationType,
    Gene,
    Mutation,
    Mutation2Annotation,
    Replicon,
    Sample,
    Sequence,
)
from rest_api.serializers import SampleSerializer


@dataclass
class SampleRaw:
    algn_file: str
    algnid: int | None
    anno_tsv_file: str
    anno_vcf_file: str
    cds_file: str
    header: str
    lift_file: str
    mafft_seqfile: str
    name: str
    properties: dict
    ref_file: str
    refmol: str
    refmolid: int
    refseq_id: int
    sampleid: int | None
    seq_file: str
    seqhash: str
    sourceid: int
    translationid: int
    tt_file: str
    var_file: str
    vcffile: str
    source_acc: str


@dataclass
class VarRaw:
    ref: str
    start: int
    end: int
    alt: str | None
    replicon_or_cds_accession: str
    type: str


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
    sample: str


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


class VCFInfoLOFRaw:
    # Predicted loss of function effects for this variant.
    gene_name: str
    gene_id: str
    number_of_transcripts_in_gene: str
    percent_of_transcripts_affected: str


class VCFInfoNMDRaw:
    # Predicted nonsense mediated decay effects for this variant.
    gene_name: str
    gene_id: str
    number_of_transcripts_in_gene: str
    percent_of_transcripts_affected: str


class SampleImport:
    def __init__(
        self,
        path: pathlib.Path,
        import_folder="import_data",
    ):
        self.sample_file_path = path
        self.import_folder = import_folder
        self.sample_raw = SampleRaw(**self._import_pickle(path))
        self.sequence: None | Sequence = None
        self.sample: None | Sample = None
        self.replicon: None | Replicon = None
        self.alignment: None | Alignment = None
        self.mutation_query_data: list[dict] = []
        self.annotation_query_data: dict[Mutation, list[dict[str, str]]] = {}
        self.db_sample_mutations: None | ValuesQuerySet[Mutation, dict[str, Any]] = None
        
        # NOTE: We probably won't need it
        # if self.sample_raw.seq_file:
        #    self.seq = "".join(
        #        [line for line in self._import_seq(self.sample_raw.seq_file)]
        #    )
        #else:
        #    raise Exception("No sequence file found")

        if self.sample_raw.var_file:
            self.vars_raw = [var for var in self._import_vars(self.sample_raw.var_file)]
        else:
            raise Exception("No var file found")
        if self.sample_raw.anno_vcf_file:
            self.anno_vcf_raw = [
                vcf_line for vcf_line in self._import_vcf(self.sample_raw.anno_vcf_file)
            ]

    # def write_to_db(self):
    #     self.sequence = Sequence.objects.get_or_create(seqhash=self.sample_raw.seqhash)[
    #         0
    #     ]
    #     self.sample = self._find_or_create_sample(self.sequence)
    #     self.replicon = Replicon.objects.get(accession=self.sample_raw.source_acc)
    #     self.alignment = Alignment.objects.get_or_create(
    #         sequence=sequence, replicon=replicon
    #     )[0]
    #     self.mutations = self._update_mutations(replicon, alignment)
    #     self._update_annotations(alignment, mutations)

    #     return sample

    def get_sequence_obj(self):
        self.sequence = Sequence(seqhash=self.sample_raw.seqhash)
        return self.sequence

    def get_sample_obj(self):
        if not self.sequence:
            raise Exception("Sequence object not created yet")
        self.sequence = Sequence.objects.get(seqhash=self.sequence.seqhash)
        self.sample = Sample(
            name=self.sample_raw.name,
            sequence=self.sequence,
            # properties=self.sample_raw.properties,
        )
        return self.sample

    def update_replicon_obj(self, replicon_cache: dict[str, Replicon]):
        if self.sample_raw.source_acc not in replicon_cache:
            replicon_cache[self.sample_raw.source_acc] = Replicon.objects.get(
                accession=self.sample_raw.source_acc
            )
        self.replicon = replicon_cache[self.sample_raw.source_acc]

    def get_alignment_obj(self):
        self.alignment = Alignment(sequence=self.sequence, replicon=self.replicon)
        return self.alignment

    def get_mutation_objs(self, gene_cache: dict[str, Gene | None]) -> list[Mutation]:
        sample_mutations = []
        self.mutation_query_data = []
        for var_raw in self.vars_raw:
            gene = None
            replicon = None
            if var_raw.type == "nt":
                replicon = Replicon.objects.get(
                    accession=var_raw.replicon_or_cds_accession
                )
                gene = Gene.objects.filter(
                    replicon=replicon, start__gte=var_raw.start, end__lte=var_raw.end
                ).first()
            elif var_raw.type == "cds":
                if not var_raw.replicon_or_cds_accession in gene_cache:
                    try:
                        gene_cache[
                            var_raw.replicon_or_cds_accession
                        ] = Gene.objects.get(
                            cds_accession=var_raw.replicon_or_cds_accession
                        )
                    except Gene.DoesNotExist:
                        gene_cache[var_raw.replicon_or_cds_accession] = None
                gene = gene_cache[var_raw.replicon_or_cds_accession]
                replicon = gene.replicon if gene else None
            mutation_data = {
                "gene": gene if gene else None,
                "ref": var_raw.ref,
                "alt": var_raw.alt,
                "start": var_raw.start,
                "end": var_raw.end,
                "replicon": self.replicon,
                "type": var_raw.type,
            }            
            # save query data for creating mutation2alignment objects later
            self.mutation_query_data.append(mutation_data)
            mutation = Mutation(**mutation_data)
            sample_mutations.append(mutation)
        return sample_mutations

    def get_mutation2alignment_objs(self) -> list:
        self.alignment = Alignment.objects.get(
            sequence=self.sequence, replicon=self.replicon
        )
        db_mutations_query = Q()
        for mutation in self.mutation_query_data:
            db_mutations_query |= Q(**mutation)
        self.db_sample_mutations = Mutation.objects.filter(db_mutations_query).values(
            "id",
            "start",
            "ref",
            "alt",
            "replicon__accession",
        )
        return [
            Mutation.alignments.through(
                alignment=self.alignment, mutation_id=mutation["id"]
            )
            for mutation in self.db_sample_mutations
        ]

    def get_annotation_objs(self) -> list[AnnotationType]:
        if self.db_sample_mutations is None:
            raise Exception("Mutation objects not created yet")
        self.annotation_query_data = {}
        for mutation in self.anno_vcf_raw:
            annotations = self._parse_vcf_info(mutation.info)
            for alt in mutation.alt.split(",") if mutation.alt else [None]:
                mut_lookup_data = {
                    "start": mutation.pos - 1,
                    "ref": mutation.ref,
                    "alt": alt,
                    "replicon__accession": mutation.chrom,
                }
                if alt and len(alt) < len(mutation.ref):
                    # deletion and alt not null
                    mut_lookup_data["start"] += 1
                    mut_lookup_data["ref"] = mut_lookup_data["ref"][1:]
                    mut_lookup_data["alt"] = None
                try:
                    db_mutation = next(
                        x
                        for x in self.db_sample_mutations
                        if all(x[k] == v for k, v in mut_lookup_data.items())
                    )
                except Mutation.DoesNotExist:
                    print(
                        f"Annotation Mutation not found using lookup: {mut_lookup_data}, varfile: {self.sample_raw.var_file} -skipping-"
                    )
                    continue
                for a in annotations:
                    for ontology in a.annotation.split("&"):
                        if not db_mutation["id"] in self.annotation_query_data.keys():
                            self.annotation_query_data[db_mutation["id"]] = []
                        self.annotation_query_data[db_mutation["id"]].append(
                            {
                                "seq_ontology": ontology,
                                "impact": a.annotation_impact,
                            }
                        )
        annotation_types = []
        for annotation in self.annotation_query_data.values():
            annotation_types.extend([AnnotationType(**data) for data in annotation])
        return annotation_types

    def get_annotation2mutation_objs(self) -> list[Mutation2Annotation]:
        db_annotations_query = Q()
        for annotation_list in self.annotation_query_data.values():
            for annotation in annotation_list:
                db_annotations_query |= Q(**annotation)
        db_annotations = AnnotationType.objects.filter(db_annotations_query)
        mutation2annotation_objs = []
        for annotation in db_annotations:
            for mutation, annotation_data_list in self.annotation_query_data.items():
                for annotation_data in annotation_data_list:
                    if (
                        annotation_data["seq_ontology"] == annotation.seq_ontology
                        and annotation_data["impact"] == annotation.impact
                    ):
                        mutation2annotation_objs.append(
                            Mutation2Annotation(
                                mutation=mutation,
                                alignment=self.alignment,
                                annotation=annotation,
                            )
                        )
        return mutation2annotation_objs

    def _parse_vcf_info(self, info) -> list[VCFInfoANNRaw]:
        # only ANN= is parsed
        if info.startswith("ANN="):
            r = re.compile(r"\(([^()]*|)*\)")
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
        return []

    def _find_or_create_sample(self, sequence):
        try:
            return Sample.objects.get(name=self.sample_raw.name, sequence=sequence)
        except Sample.DoesNotExist:
            sample_serializer = SampleSerializer(
                data={
                    "name": self.sample_raw.name,
                    "sequence": sequence.id,
                    "properties": self.sample_raw.properties,
                }
            )
            sample_serializer.is_valid(raise_exception=True)
            return sample_serializer.save()

    def _import_pickle(self, path: str):
        with open(path, "rb") as f:
            return pickle.load(f)

    def _import_vars(self, path):
        file_name = pathlib.Path(path).name
        self.var_file_path = (
            pathlib.Path(self.import_folder)
            .joinpath("var")
            .joinpath(file_name[:2])
            .joinpath(file_name)
        )
        with open(self.var_file_path, "r") as handle:
            for line in handle:
                if line == "//":
                    break
                var_raw = line.strip("\r\n").split("\t")
                yield VarRaw(
                    var_raw[0],  # ref
                    int(var_raw[1]),  # start
                    int(var_raw[2]),  # end
                    None if var_raw[3] == " " else var_raw[3],  # alt
                    var_raw[4],  # replicon_or_cds_accession
                    var_raw[6],  # type
                )

    def _import_vcf(self, path):
        file_name = pathlib.Path(path).name
        self.vcf_file_path = (
            pathlib.Path(self.import_folder)
            .joinpath("anno")
            .joinpath(file_name[:2])
            .joinpath(file_name)
        )
        try:
            with open(self.vcf_file_path, "r") as handle:
                for line in handle:
                    if line.startswith("#"):
                        continue
                    vcf_raw = line.strip("\r\n").split("\t")
                    yield VCFRaw(
                        chrom=vcf_raw[0],
                        pos=int(vcf_raw[1]),
                        id=vcf_raw[2],
                        ref=vcf_raw[3],
                        alt=None if vcf_raw[4] == "." else vcf_raw[4],
                        qual=vcf_raw[5],
                        filter=vcf_raw[6],
                        info=vcf_raw[7],
                        format=vcf_raw[8],
                        sample=vcf_raw[9],
                    )
        except FileNotFoundError:
            return

    def _import_seq(self, path):
        file_name = pathlib.Path(path).name
        self.seq_file_path = (
            pathlib.Path(self.import_folder)
            .joinpath("seq")
            .joinpath(file_name[:2])
            .joinpath(file_name)
        )
        with open(self.seq_file_path, "r") as handle:
            for line in handle:
                yield line.strip("\r\n")

    def move_files(self, success):
        # dont move files for now
        return
        for file in [
            self.sample_file_path,
            self.var_file_path,
            self.seq_file_path,
        ]:
            import_data_location = pathlib.Path(file).parent.parent.parent
            folder_structure = pathlib.Path(file).relative_to(import_data_location)
            if success:
                target_folder = pathlib.Path(import_data_location).joinpath(
                    "imported_successfully"
                )
            else:
                target_folder = pathlib.Path(import_data_location).joinpath(
                    "failed_import"
                )
            target_folder.joinpath(folder_structure.parent).mkdir(
                parents=True, exist_ok=True
            )
            pathlib.Path(file).rename(target_folder.joinpath(folder_structure))
