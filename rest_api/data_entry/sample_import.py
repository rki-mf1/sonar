import pathlib
import pickle
import re
import typing
from dataclasses import dataclass
from typing import Any
from django.core.cache import cache
from django.db.models import Q

if typing.TYPE_CHECKING:
    from django.db.models.query import ValuesQuerySet

from covsonar_backend.settings import LOGGER
from rest_api.models import (
    Alignment,
    AnnotationType,
    Gene,
    ImportLog,
    Mutation,
    Mutation2Annotation,
    Replicon,
    Sample,
    Sequence,
)
from rest_api.serializers import SampleSerializer
from typing import Optional


@dataclass
class SampleRaw:
    anno_vcf_file: str
    cds_file: str
    header: str
    mafft_seqfile: str
    name: str
    properties: dict
    ref_file: str
    refmol: str
    refmolid: int
    seq_file: str
    seqhash: str
    sourceid: int
    translationid: int
    tt_file: Optional[str] = None
    var_file: Optional[str] = None
    vcffile: Optional[str] = None
    algnid: Optional[int] = None
    sampleid: Optional[int] = None
    refseq_id: Optional[int] = None
    source_acc: Optional[str] = None
    algn_file: Optional[str] = None
    anno_tsv_file: Optional[str] = None
    lift_file: Optional[str] = None


@dataclass
class VarRaw:
    ref: str
    start: int
    end: int
    alt: str | None
    replicon_or_cds_accession: str
    type: str


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
        self.success = False
        # NOTE: We probably won't need it
        # if self.sample_raw.seq_file:
        #    self.seq = "".join(
        #        [line for line in self._import_seq(self.sample_raw.seq_file)]
        #    )
        # else:
        #    raise Exception("No sequence file found")

        if self.sample_raw.var_file:
            self.vars_raw = [var for var in self._import_vars(self.sample_raw.var_file)]
        else:
            raise Exception("No var file found")        

    def get_sample_name(self):
        return self.sample_raw.name

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

    def get_mutation2alignment_objs(self, batch_size=100) -> list:
        self.alignment = Alignment.objects.get(
            sequence=self.sequence, replicon=self.replicon
        )

        mutation_alignment_objs = []
        for i in range(0, len(self.mutation_query_data), batch_size):
            batch_mutation_query_data = self.mutation_query_data[i:i+batch_size]
            db_mutations_query = Q()
            for mutation in batch_mutation_query_data:
                db_mutations_query |= Q(**mutation)
            
            db_sample_mutations = Mutation.objects.filter(db_mutations_query).values(
                "id",
                "start",
                "ref",
                "alt",
                "replicon__accession",
            )
            for j in range(0, len(db_sample_mutations), batch_size):
                batch_mutations = db_sample_mutations[j:j+batch_size]
                batch_alignment_objs = []
                for mutation in batch_mutations:
                    batch_alignment_objs.append(
                        Mutation.alignments.through(
                            alignment=self.alignment, mutation_id=mutation["id"]
                        )
                    )
                mutation_alignment_objs.extend(batch_alignment_objs)

        return mutation_alignment_objs

    def get_annotation_objs(self) -> list[AnnotationType]:
        if self.db_sample_mutations is None:
            LOGGER.error("Mutation objects not created yet")
            raise Exception("Mutation objects not created yet")
        self.annotation_query_data = {}
        for mutation in self.anno_vcf_raw:
            annotations = []
            for annotation in [
                self._parse_vcf_info(info) for info in mutation.info.split(";") if info
            ]:
                if annotation:
                    annotations.extend(annotation)
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
                    if a:  # skip None type
                        for ontology in a.annotation.split("&"):
                            if (
                                not db_mutation["id"]
                                in self.annotation_query_data.keys()
                            ):
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
            for mutation_id, annotation_data_list in self.annotation_query_data.items():
                for annotation_data in annotation_data_list:
                    if (
                        annotation_data["seq_ontology"] == annotation.seq_ontology
                        and annotation_data["impact"] == annotation.impact
                    ):
                        mutation2annotation_objs.append(
                            Mutation2Annotation(
                                mutation_id=mutation_id,
                                alignment=self.alignment,
                                annotation=annotation,
                            )
                        )

        return mutation2annotation_objs

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
