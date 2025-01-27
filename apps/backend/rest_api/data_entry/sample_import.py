from dataclasses import dataclass
import pathlib
import pickle
import typing
from typing import Any
from typing import Optional

from django.utils import timezone
import pandas as pd

from covsonar_backend.settings import LOGGER
from rest_api.models import Alignment
from rest_api.models import AminoAcidMutation
from rest_api.models import Gene
from rest_api.models import NucleotideMutation
from rest_api.models import Replicon
from rest_api.models import Sample
from rest_api.models import Sequence


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
    sample_sequence_length: int
    sourceid: int
    translationid: int
    include_nx: bool
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
    id: int
    ref: str
    start: int
    end: int
    alt: str | None
    replicon_or_cds_accession: str
    # lable: str
    type: str
    parent_id: list[int] | None


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
        self.success = False

        if self.sample_raw.var_file:
            self.vars_raw = [
                var
                for var in self._import_vars(
                    self.sample_raw.var_file, self.sample_raw.include_nx
                )
            ]
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
            length=self.sample_raw.sample_sequence_length,
            last_update_date=timezone.now(),
            # properties=self.sample_raw.properties,
        )
        return self.sample

    def update_replicon_obj(self, replicon_cache: dict[str, Replicon]):
        if self.sample_raw.source_acc not in replicon_cache:
            replicon_cache[self.sample_raw.source_acc] = Replicon.objects.get(
                accession=self.sample_raw.source_acc
            )
        self.replicon = replicon_cache[self.sample_raw.source_acc]

    def create_alignment(self, alignments_list: list[Alignment]):
        self.alignment = next(
            filter(
                lambda x: x.sequence == self.sequence and x.replicon == self.replicon,
                alignments_list,
            ),
            None,
        )
        if not self.alignment:
            self.alignment = Alignment(sequence=self.sequence, replicon=self.replicon)
            alignments_list.append(self.alignment)

    def get_mutation_objs_nt(
        self,
        nt_mutation_set: list[NucleotideMutation],
        replicon_cache: dict[str, Replicon | None],
        gene_cache_by_var_pos: dict[Replicon | None, dict[int, dict[int, Gene | None]]],
        nt_mutation_alignment_relations: list[NucleotideMutation.alignments.through],
    ) -> dict[int, NucleotideMutation]:
        import_id_to_sample_mutations: dict[int, NucleotideMutation] = {}
        for var_raw in self.vars_raw:
            replicon = None
            if var_raw.type == "nt":
                if not var_raw.replicon_or_cds_accession in replicon_cache:
                    replicon_cache[var_raw.replicon_or_cds_accession] = (
                        Replicon.objects.get(
                            accession=var_raw.replicon_or_cds_accession
                        )
                    )
                replicon = replicon_cache[var_raw.replicon_or_cds_accession]
                if not replicon in gene_cache_by_var_pos:
                    gene_cache_by_var_pos[replicon] = {}
                if not var_raw.start in gene_cache_by_var_pos[replicon]:
                    gene_cache_by_var_pos[replicon][var_raw.start] = {}
                if not var_raw.end in gene_cache_by_var_pos[replicon][var_raw.start]:
                    gene_cache_by_var_pos[replicon][var_raw.start][var_raw.end] = (
                        Gene.objects.filter(
                            replicon=replicon,
                            start__gte=var_raw.start,
                            end__lte=var_raw.end,
                        ).first()
                    )
                gene = gene_cache_by_var_pos[replicon][var_raw.start][var_raw.end]
                # in DEL, we dont keep REF in the database.
                if var_raw.alt is None:
                    var_raw.ref = ""

                mutation_data = {
                    "ref": var_raw.ref if var_raw.ref else "",
                    "alt": var_raw.alt if var_raw.alt else "",
                    "start": var_raw.start,
                    "end": var_raw.end,
                    "replicon": self.replicon,
                }
                mutation = next(
                    filter(
                        lambda x: self.is_same_mutation(mutation_data, x),
                        nt_mutation_set,
                    ),
                    None,
                )
                if not mutation:
                    mutation = NucleotideMutation(**mutation_data)
                    nt_mutation_set.append(mutation)
                nt_mutation_alignment_relations.append(
                    NucleotideMutation.alignments.through(
                        nucleotidemutation=mutation, alignment=self.alignment
                    )
                )
                import_id_to_sample_mutations[var_raw.id] = mutation
        return import_id_to_sample_mutations

    def is_same_mutation(
        self, mutation_data: dict, mutation: NucleotideMutation | AminoAcidMutation
    ) -> bool:
        return all(getattr(mutation, k) == v for k, v in mutation_data.items())

    def get_mutation_objs_cds_and_parent_relations(
        self,
        cds_mutation_set: list[AminoAcidMutation],
        gene_cache_by_accession: dict[str, Gene | None],
        parent_id_mapping: dict[int, NucleotideMutation],
        aa_mutation_alignment_relations: list[AminoAcidMutation.alignments.through],
    ) -> list[AminoAcidMutation.parent.through]:
        sample_cds_mutations: list[AminoAcidMutation] = []
        mutation_parent_relations = []
        for var_raw in self.vars_raw:
            if var_raw.type == "cds":
                if not var_raw.replicon_or_cds_accession in gene_cache_by_accession:
                    try:
                        gene_cache_by_accession[var_raw.replicon_or_cds_accession] = (
                            Gene.objects.get(
                                cds_accession=var_raw.replicon_or_cds_accession
                            )
                        )
                    except Gene.DoesNotExist:
                        LOGGER.error(
                            f"Gene not found for accession: {var_raw.replicon_or_cds_accession}"
                        )
                        continue
                gene = gene_cache_by_accession[var_raw.replicon_or_cds_accession]
                if var_raw.alt is None:
                    var_raw.ref = ""
                mutation_data = {
                    "gene": gene,
                    "ref": var_raw.ref if var_raw.ref else "",
                    "alt": var_raw.alt if var_raw.alt else "",
                    "start": var_raw.start if var_raw.start else 0,
                    "end": var_raw.end if var_raw.end else 0,
                    "replicon": self.replicon,
                }
                mutation = next(
                    filter(
                        lambda x: self.is_same_mutation(mutation_data, x),
                        cds_mutation_set,
                    ),
                    None,
                )
                if not mutation:
                    mutation = AminoAcidMutation(**mutation_data)
                    cds_mutation_set.append(mutation)
                aa_mutation_alignment_relations.append(
                    AminoAcidMutation.alignments.through(
                        aminoacidmutation=mutation, alignment=self.alignment
                    )
                )
                if var_raw.parent_id:
                    mutation_parent_relations.extend(
                        AminoAcidMutation.parent.through(
                            aminoacidmutation=mutation,
                            nucleotidemutation=parent_id_mapping[parent_id],
                        )
                        for parent_id in var_raw.parent_id
                    )
                sample_cds_mutations.append(mutation)
        return mutation_parent_relations

    def _import_pickle(self, path: str):
        with open(path, "rb") as f:
            return pickle.load(f)

    def _import_vars(self, path, include_nx: bool):
        file_name = pathlib.Path(path).name
        self.var_file_path = (
            pathlib.Path(self.import_folder)
            .joinpath("var")
            .joinpath(file_name[:2])
            .joinpath(file_name)
        )
        var_df = pd.read_csv(self.var_file_path, sep="\t")
        var_df[["ref", "alt"]] = var_df[["ref", "alt"]].fillna("").replace({" ": ""})

        if not include_nx:
            # remove all ref containing Ns for nt, or X for cds
            var_df = var_df[
                ~((var_df["type"] == "nt") & var_df["alt"].str.contains("N", na=False))
            ]
            var_df = var_df[
                ~((var_df["type"] == "cds") & var_df["alt"].str.contains("X", na=False))
            ]

        for _, row in var_df.iterrows():
            yield VarRaw(
                int(row["id"]),
                row["ref"],
                int(row["start"]),
                int(row["end"]),
                row["alt"],
                row["reference_acc"],
                row["type"],
                (
                    [int(x) for x in row["parent_id"].split(",")]
                    if pd.notna(row["parent_id"])
                    else None
                ),
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
