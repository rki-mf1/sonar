import pathlib
import pickle
from dataclasses import dataclass
import re

from django.db.models import Q, QuerySet

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
        if self.sample_raw.seq_file:
            self.seq = "".join(
                [line for line in self._import_seq(self.sample_raw.seq_file)]
            )
        else:
            raise Exception("No sequence file found")
        if self.sample_raw.var_file:
            self.vars_raw = [var for var in self._import_vars(self.sample_raw.var_file)]
        else:
            raise Exception("No var file found")
        if self.sample_raw.anno_vcf_file:
            self.vcf_raw = [
                vcf_line for vcf_line in self._import_vcf(self.sample_raw.anno_vcf_file)
            ]

    def write_to_db(self):
        sequence = Sequence.objects.get_or_create(seqhash=self.sample_raw.seqhash)[0]
        sample = self._find_or_create_sample(sequence)
        replicon = Replicon.objects.get(accession=self.sample_raw.source_acc)
        alignment = Alignment.objects.get_or_create(
            sequence=sequence, replicon=replicon
        )[0]
        mutations = self._update_mutations(replicon, alignment)
        self._update_annotations(alignment, mutations)

        return sample

    def _update_mutations(self, replicon, alignment):
        sample_mutations = []
        query_data = []
        # sort mutation data from raw data
        for var_raw in self.vars_raw:
            gene = None
            if var_raw.type == "nt":
                replicon = Replicon.objects.get(
                    accession=var_raw.replicon_or_cds_accession
                )
                gene = Gene.objects.filter(
                    replicon=replicon, start__gte=var_raw.start, end__lte=var_raw.end
                ).first()
            elif var_raw.type == "cds":
                try:
                    gene = Gene.objects.get(
                        cds_accession=var_raw.replicon_or_cds_accession
                    )
                    replicon = gene.replicon
                except Gene.DoesNotExist:
                    pass
            mutation_data = {
                "gene": gene if gene else None,
                "ref": var_raw.ref,
                "alt": var_raw.alt,
                "start": var_raw.start,
                "end": var_raw.end,
                "replicon": replicon,
                "type": var_raw.type,
            }
            query_data.append(mutation_data)
            mutation = Mutation(**mutation_data)
            sample_mutations.append(mutation)
        # create mutations if they don't exist (will not return existing ones)
        Mutation.objects.bulk_create(sample_mutations, ignore_conflicts=True)
        # select all mutations for this sample
        db_mutations_query = Q()
        for mutation in query_data:
            db_mutations_query |= Q(**mutation)
        db_sample_mutations = Mutation.objects.filter(db_mutations_query)
        # create relations between mutations and alignments
        Mutation.alignments.through.objects.bulk_create(
            [
                Mutation.alignments.through(alignment=alignment, mutation=mutation)
                for mutation in db_sample_mutations
            ]
        )
        return db_sample_mutations

    def _update_annotations(self, alignment, db_mutations: QuerySet[Mutation]):
        mutation2annotation_objects = []
        for mutation in self.vcf_raw:
            mut_lookup_data = {
                "start": mutation.pos - 1,
                "ref": mutation.ref,
                "alt": mutation.alt,
                "replicon__accession": mutation.chrom,
            }
            if mutation.alt and len(mutation.alt) < len(mutation.ref):
                # deletion and alt not null
                mut_lookup_data["start"] += 1
                mut_lookup_data["ref"] = mut_lookup_data["ref"][1:]
                mut_lookup_data["alt"] = None
            try:
                db_mutation = db_mutations.get(**mut_lookup_data)
            except Mutation.DoesNotExist:
                print(
                    f"Annotation Mutation not found using lookup: {mut_lookup_data}, varfile: {self.sample_raw.var_file} -skipping-"
                )
                continue
            annotations = self._parse_vcf_info(mutation.info)
            annotation_data = [
                {
                    "seq_ontology": a.annotation,
                    "impact": a.annotation_impact,
                }
                for a in annotations
            ]
            AnnotationType.objects.bulk_create(
                [AnnotationType(**data) for data in annotation_data],
                ignore_conflicts=True,
            )
            db_annotations_query = Q()
            for annotation in annotation_data:
                db_annotations_query |= Q(**annotation)
            db_annotations = AnnotationType.objects.filter(db_annotations_query)
            mutation2annotation_objects.extend(
                [
                    Mutation2Annotation(
                        mutation=db_mutation,
                        alignment=alignment,
                        annotation=annotation,
                    )
                    for annotation in db_annotations
                ]
            )
        Mutation2Annotation.objects.bulk_create(
            mutation2annotation_objects, ignore_conflicts=True
        )

    def _parse_vcf_info(self, info) -> list[VCFInfoANNRaw]:
        # only ANN= is parsed
        if info.startswith("ANN="):
            # r = re.compile(r"\(([^()]*|(?R))*\)")
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
