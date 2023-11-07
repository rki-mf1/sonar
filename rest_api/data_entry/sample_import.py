import pathlib
import pickle
from dataclasses import dataclass

from django.db.models import Q

from rest_api.models import Alignment, Gene, Mutation, Replicon, Sample, Sequence
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


class SampleImport:
    def __init__(
        self,
        path: pathlib.Path,
        import_folder="import_data",
    ):
        self.sample_file_path = path
        self.import_folder = import_folder
        self.sample_raw = SampleRaw(**self._import_pickle(path))
        self.vars_raw = [var for var in self._import_vars(self.sample_raw.var_file)]
        self.seq = "".join(
            [line for line in self._import_seq(self.sample_raw.seq_file)]
        )

    def write_to_db(self):
        sequence = Sequence.objects.get_or_create(seqhash=self.sample_raw.seqhash)[0]
        sample = self._find_or_create_sample(sequence)
        replicon = Replicon.objects.get(accession=self.sample_raw.source_acc)
        alignment = Alignment.objects.get_or_create(
            sequence=sequence, replicon=replicon
        )[0]
        mutations = []
        query_data = []
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
            mutations.append(mutation)
        Mutation.objects.bulk_create(mutations, ignore_conflicts=True)
        # select mutations that were just created
        refreshed_mutations = Q()
        for mutation in query_data:
            refreshed_mutations |= Q(**mutation)
        saved_mutations = Mutation.objects.filter(refreshed_mutations)
        Mutation.alignments.through.objects.bulk_create(
            [
                Mutation.alignments.through(alignment=alignment, mutation=mutation)
                for mutation in saved_mutations
            ]
        )
        return sample

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
