from dataclasses import dataclass
import pathlib
import pickle
import typing
from typing import Any
from typing import Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_api.models import Alignment
from rest_api.models import Gene
from rest_api.models import Mutation
from rest_api.models import Replicon
from rest_api.models import Sample
from rest_api.models import Sequence

if typing.TYPE_CHECKING:
    from django.db.models.query import ValuesQuerySet


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
    parent_id: int | None


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

    def create_alignment(self):
        self.alignment = Alignment.objects.get_or_create(
            sequence=self.sequence, replicon=self.replicon
        )[0]
        return self.alignment

    def get_mutation_objs_V2(
        self,
        gene_cache_by_accession: dict[str, Gene | None],
        replicon_cache: dict[str, Replicon | None],
        gene_cache_by_var_pos: dict[Replicon | None, dict[int, dict[int, Gene | None]]],
    ) -> list[Mutation]:
        sample_mutations = []
        self.mutation_query_data = []
        # Separate NT and CDS mutations
        nt_vars = [var_raw for var_raw in self.vars_raw if var_raw.type == "nt"]
        cds_vars = [var_raw for var_raw in self.vars_raw if var_raw.type == "cds"]
        # Insert NT mutations and do mapping of original IDs to database IDs
        nt_id_mapping = {}
        nt_mutations = []
        for var_raw in nt_vars:
            gene = None
            replicon = None
            if not var_raw.replicon_or_cds_accession in replicon_cache:
                replicon_cache[var_raw.replicon_or_cds_accession] = (
                    Replicon.objects.get(accession=var_raw.replicon_or_cds_accession)
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

            # In DEL, we don't keep REF in the database.
            if var_raw.alt is None:
                var_raw.ref = ""

            mutation_data = {
                "gene": gene if gene else None,
                "ref": var_raw.ref,
                "alt": var_raw.alt,
                "start": var_raw.start,
                "end": var_raw.end,
                "replicon": replicon,
                "type": var_raw.type,
            }

            # Use get_or_create to ensure we have the mutation and its ID
            mutation, created = Mutation.objects.get_or_create(**mutation_data)
            nt_mutations.append(mutation)
            nt_id_mapping[var_raw.id] = mutation.id
            self.mutation_query_data.append(mutation_data)

        # seem the bulk_create with setting the ignore_conflicts will disable returning ID
        # https://docs.djangoproject.com/en/4.2/ref/models/querysets/#bulk-create

        # V.3 ------------------------------
        # Mutation.objects.get_or_create

        # V.2 ------------------------------
        # optimize for performance (be careful about order!!)
        # a single query with OR conditions for all mutations
        # query = Q()
        # for nt in nt_mutations:
        #     query |= Q(
        #         gene=nt.gene,
        #         ref=nt.ref,
        #         alt=nt.alt,
        #         start=nt.start,
        #         end=nt.end,
        #         replicon=nt.replicon,
        #         type=nt.type,
        #     )
        # inserted_rows = Mutation.objects.filter(query).order_by('')

        # # Create a dictionary mapping (ref, alt, start, end, replicon, type) to mutation IDs
        # inserted_mapping = {
        #     (
        #         mutation.ref,
        #         mutation.alt,
        #         mutation.start,
        #         mutation.end,
        #         mutation.replicon_id,
        #         mutation.type,
        #     ): mutation.id
        #     for mutation in inserted_rows
        # }

        # # Map back to var_raw.id
        # nt_id_mapping = {
        #     var_raw.id: inserted_mapping.get(
        #         (nt.ref, nt.alt, nt.start, nt.end, nt.replicon.id, nt.type), None
        #     )
        #     for nt, var_raw in zip(nt_mutations, nt_vars)
        # }

        # V.1 ------------------------------
        # # Fetch the inserted rows and map their IDs back
        # #  a dictionary to map `var_raw` IDs to mutation IDs
        # nt_id_mapping = {}
        # # Iterate over nt_mutations and nt_vars to perform exact matching
        # # order is matter!
        # for nt, var_raw in zip(nt_mutations, nt_vars):
        #     # Perform exact match for this specific mutation
        #     mutation = Mutation.objects.get(
        #         gene=nt.gene,
        #         ref=nt.ref,
        #         alt=nt.alt,
        #         start=nt.start,
        #         end=nt.end,
        #         replicon=nt.replicon,
        #         type=nt.type,
        #     )
        #     # Map the var_raw.id to the mutation ID
        #     nt_id_mapping[var_raw.id] = mutation.id
        # ----------------

        # for CDS mutations
        # For CDS mutations
        cds_mutations = []
        for var_raw in cds_vars:
            # Update parent IDs for CDS mutations
            parent_id = nt_id_mapping.get(var_raw.parent_id, None)
            gene = None
            replicon = None

            # Retrieve or cache the gene and replicon
            if var_raw.replicon_or_cds_accession not in gene_cache_by_accession:
                try:
                    gene_cache_by_accession[var_raw.replicon_or_cds_accession] = (
                        Gene.objects.get(
                            cds_accession=var_raw.replicon_or_cds_accession
                        )
                    )
                except Gene.DoesNotExist:
                    gene_cache_by_accession[var_raw.replicon_or_cds_accession] = None

            gene = gene_cache_by_accession[var_raw.replicon_or_cds_accession]
            replicon = gene.replicon if gene else None

            # In DEL, we don't keep REF in the database.
            if var_raw.alt is None:
                var_raw.ref = ""

            mutation_data = {
                "gene": gene if gene else None,
                "ref": var_raw.ref,
                "alt": var_raw.alt,
                "start": var_raw.start,
                "end": var_raw.end,
                "replicon": replicon,
                "type": var_raw.type,
                # "parent_id": parent_id,  # Updated parent ID
            }

            # Check if the mutation exists
            try:
                mutation = Mutation.objects.get(**mutation_data)
                # If it exists, update the parent_id (or any other field you want to modify)
                mutation.parent_id = parent_id
                mutation.save()
            except Mutation.DoesNotExist:
                # If it does not exist, create a new one
                mutation = Mutation.objects.create(**mutation_data, parent_id=parent_id)

            # Add mutation to list (for further processing if needed)
            cds_mutations.append(mutation)
            self.mutation_query_data.append(mutation_data)

        # Bulk insert CDS mutations

        # Mutation.objects.bulk_create(cds_mutations, update_conflicts=True,
        #     update_fields=["parent_id"],
        #     unique_fields=["ref", "alt", "start", "end", "type", "gene_id", "replicon_id"],)

        # Combine NT and CDS mutations into the result
        # we might dont need sample_mutations because
        # we insert data into database in this function
        sample_mutations.extend(nt_mutations)
        sample_mutations.extend(cds_mutations)

        return sample_mutations

    def get_mutation_objs(
        self,
        gene_cache_by_accession: dict[str, Gene | None],
        replicon_cache: dict[str, Replicon | None],
        gene_cache_by_var_pos: dict[Replicon | None, dict[int, dict[int, Gene | None]]],
    ) -> list[Mutation]:
        sample_mutations = []
        self.mutation_query_data = []
        for var_raw in self.vars_raw:
            gene = None
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
            elif var_raw.type == "cds":
                if not var_raw.replicon_or_cds_accession in gene_cache_by_accession:
                    try:
                        gene_cache_by_accession[var_raw.replicon_or_cds_accession] = (
                            Gene.objects.get(
                                cds_accession=var_raw.replicon_or_cds_accession
                            )
                        )
                    except Gene.DoesNotExist:
                        gene_cache_by_accession[var_raw.replicon_or_cds_accession] = (
                            None
                        )
                gene = gene_cache_by_accession[var_raw.replicon_or_cds_accession]
                replicon = gene.replicon if gene else None
            # in DEL, we dont keep REF in the database.
            if var_raw.alt is None:
                var_raw.ref = ""

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
        # self.alignment = Alignment.objects.get(
        #     sequence=self.sequence, replicon=self.replicon
        # )
        # Determine batch size dynamically based on the length of mutation_query_data
        data_length = len(self.mutation_query_data)

        # a minimum and maximum batch size
        MIN_BATCH_SIZE = 100
        MAX_BATCH_SIZE = 5000

        # Dynamic batch size based on data length
        if data_length <= MAX_BATCH_SIZE:
            # If the data length is smaller than MAX_BATCH_SIZE, use 20% - 50% for example,
            # of the data length as the batch size.
            # we can adjust 0.40 to other percentages like 0.50
            batch_size = max(MIN_BATCH_SIZE, int(data_length * 0.50))
        else:
            # Set batch size to 1% of the total dataset size
            batch_size = max(MIN_BATCH_SIZE, min(MAX_BATCH_SIZE, data_length // 100))

        mutation_alignment_objs = []
        for i in range(0, len(self.mutation_query_data), batch_size):
            batch_mutation_query_data = self.mutation_query_data[i : i + batch_size]
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
                batch_mutations = db_sample_mutations[j : j + batch_size]
                batch_alignment_objs = []
                for mutation in batch_mutations:
                    batch_alignment_objs.append(
                        Mutation.alignments.through(
                            alignment=self.alignment, mutation_id=mutation["id"]
                        )
                    )
                mutation_alignment_objs.extend(batch_alignment_objs)

        return mutation_alignment_objs

    # deprecated function
    # def get_annotation_objs(self) -> list[AnnotationType]:
    #     if self.db_sample_mutations is None:
    #         LOGGER.error("Mutation objects not created yet")
    #         raise Exception("Mutation objects not created yet")
    #     self.annotation_query_data = {}
    #     for mutation in self.anno_vcf_raw:
    #         annotations = []
    #         for annotation in [
    #             self._parse_vcf_info(info) for info in mutation.info.split(";") if info
    #         ]:
    #             if annotation:
    #                 annotations.extend(annotation)
    #         for alt in mutation.alt.split(",") if mutation.alt else [None]:
    #             mut_lookup_data = {
    #                 "start": mutation.pos - 1,
    #                 "ref": mutation.ref,
    #                 "alt": alt,
    #                 "replicon__accession": mutation.chrom,
    #             }
    #             if alt and len(alt) < len(mutation.ref):
    #                 # deletion and alt not null
    #                 mut_lookup_data["start"] += 1
    #                 mut_lookup_data["ref"] = mut_lookup_data["ref"][1:]
    #                 mut_lookup_data["alt"] = None

    #             try:
    #                 db_mutation = next(
    #                     x
    #                     for x in self.db_sample_mutations
    #                     if all(x[k] == v for k, v in mut_lookup_data.items())
    #                 )
    #             except Mutation.DoesNotExist:
    #                 print(
    #                     f"Annotation Mutation not found using lookup: {mut_lookup_data}, varfile: {self.sample_raw.var_file} -skipping-"
    #                 )
    #                 continue
    #             for a in annotations:
    #                 if a:  # skip None type
    #                     for ontology in a.annotation.split("&"):
    #                         if (
    #                             not db_mutation["id"]
    #                             in self.annotation_query_data.keys()
    #                         ):
    #                             self.annotation_query_data[db_mutation["id"]] = []
    #                         self.annotation_query_data[db_mutation["id"]].append(
    #                             {
    #                                 "seq_ontology": ontology,
    #                                 "impact": a.annotation_impact,
    #                             }
    #                         )
    #     annotation_types = []
    #     for annotation in self.annotation_query_data.values():
    #         annotation_types.extend([AnnotationType(**data) for data in annotation])
    #     return annotation_types

    # # deprecated function
    # def get_annotation2mutation_objs(self) -> list[Mutation2Annotation]:
    #     db_annotations_query = Q()
    #     for annotation_list in self.annotation_query_data.values():
    #         for annotation in annotation_list:
    #             db_annotations_query |= Q(**annotation)
    #     db_annotations = AnnotationType.objects.filter(db_annotations_query)
    #     mutation2annotation_objs = []
    #     for annotation in db_annotations:
    #         for mutation_id, annotation_data_list in self.annotation_query_data.items():
    #             for annotation_data in annotation_data_list:
    #                 if (
    #                     annotation_data["seq_ontology"] == annotation.seq_ontology
    #                     and annotation_data["impact"] == annotation.impact
    #                 ):
    #                     mutation2annotation_objs.append(
    #                         Mutation2Annotation(
    #                             mutation_id=mutation_id,
    #                             alignment=self.alignment,
    #                             annotation=annotation,
    #                         )
    #                     )

    #     return mutation2annotation_objs

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
                    var_raw[0],  # id
                    var_raw[1],  # ref
                    int(var_raw[2]),  # start
                    int(var_raw[3]),  # end
                    None if var_raw[4] == " " else var_raw[4],  # alt
                    var_raw[5],  # replicon_or_cds_accession
                    # var_raw[6],  # label
                    var_raw[7],  # type
                    var_raw[8] if len(var_raw) > 8 else None,  # parent_id
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
