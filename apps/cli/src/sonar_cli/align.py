from itertools import count
import os
import re
import sys
from typing import Generator
from typing import List
from typing import Tuple
import warnings

from Bio import BiopythonWarning
from Bio.Seq import Seq
import numpy as np
import pandas as pd
from sonar_cli.common_aligns import align_MAFFT
from sonar_cli.common_aligns import align_Parasail
from sonar_cli.common_aligns import align_WFA
from sonar_cli.common_utils import read_seqcache
from sonar_cli.config import TMP_CACHE
from sonar_cli.logging import LoggingConfigurator

warnings.simplefilter("ignore", BiopythonWarning)

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()


class sonarAligner:
    def __init__(self, cache_outdir=None, method=1, allow_updates=False):
        self.nuc_profile = []
        self.nuc_n_profile = []
        self.aa_profile = []
        self.aa_n_profile = []
        self.cigar_pattern = re.compile(r"(\d+)(\D)")
        self.outdir = TMP_CACHE if not cache_outdir else os.path.abspath(cache_outdir)
        self.method = method
        self.allow_updates = allow_updates

    def process_cached_sample(self, **sample_data: dict):
        if self.method == 1:  # MAFFT
            self.process_cached_v1(sample_data)
        elif self.method == 2 or self.method == 3:  # Parasail,WFA2-lib
            self.process_cached_v2(sample_data, self.method)
        return

    def process_cached_v1(self, data: dict):
        """
        Work with: Emboss Stretcher, MAFFT
        This function takes a sample file and processes it.
        create var file with NT and AA mutations
        """

        # if not self.allow_updates:
        # SKIP aligning sequences and call var_file again (i.e., skipping existing files in the cache).
        # else: overwrite.
        # NOTE: If the file contents change, the hash file name will also change.
        if not self.allow_updates:

            if data["var_file"] is None:
                return True
            elif os.path.isfile(data["var_file"]):
                with open(data["var_file"], "r") as handle:
                    for line in handle:
                        pass
                    if line == "//":
                        return True

        source_acc = str(data["source_acc"])
        alignment = align_MAFFT(data["seq_file"], data["ref_file"])

        # NOTE: this line was already performant
        nuc_vars = [x for x in self.extract_vars(*alignment, elem_acc=source_acc)]

        # NOTE: uncomment the code below to change the varaint extraction to the Cigar stlye
        # cigar = self.gen_cigar(alignment[0], alignment[1])
        # nuc_vars = [
        #    x
        #    for x in self.extract_vars_from_cigar(
        #        alignment[0], alignment[1], cigar, source_acc, data["cds_file"]
        #    )
        # ]
        # empty string for parent_id row
        vars = "\n".join(["\t".join(x + ("",)) for x in nuc_vars])
        # print(nuc_vars)
        if nuc_vars:
            # create AA mutation
            aa_vars = "\n".join(
                # NOTE: this line is actually cause the the slow performance
                ["\t".join(x) for x in self.lift_vars(nuc_vars, data["lift_file"])]
            )
            if aa_vars:
                # concatinate to the same file of NT variants
                vars += "\n" + aa_vars
            vars += "\n"

        try:
            with open(data["var_file"], "w") as handle:
                handle.write(
                    "#"
                    + "\t".join(
                        [
                            "id",
                            "ref",
                            "start",
                            "end",
                            "alt",
                            "accs",
                            "label",
                            "type",
                            "parent_id",
                        ]
                    )
                    + "\n"
                )
                handle.write(vars + "//")
        except OSError:
            os.makedirs(os.path.dirname(data["var_file"]), exist_ok=True)
            with open(data["var_file"], "w") as handle:
                handle.write(
                    "#"
                    + "\t".join(
                        [
                            "id",
                            "ref",
                            "start",
                            "end",
                            "alt",
                            "accs",
                            "label",
                            "type",
                            "parent_id",
                        ]
                    )
                    + "\n"
                )
                handle.write(vars + "//")
        return

    def process_cached_v2(self, data: dict, method: int):  # noqa: C901
        """
        Work with: Cigar format
        This function takes a sample file and processes it.
        create var file with NT and AA mutations
        """
        if not self.allow_updates:
            if data["var_file"] is None:
                return True
            elif os.path.isfile(data["var_file"]):
                with open(data["var_file"], "r") as handle:
                    for line in handle:
                        pass
                if line == "//":
                    return True

        # elemid = str(data["sourceid"])
        source_acc = str(data["source_acc"])
        qryseq = read_seqcache(data["seq_file"])
        refseq = read_seqcache(data["ref_file"])

        if method == 2:
            _, __, cigar = align_Parasail(qryseq, refseq)
        # TODO: WFA is disabled for now. It has problems with crashing and also
        # needs to be updated now that qryseq and refseq are fasta files
        # (previously they were pure sequences)
        # elif method == 3:
        #    _, __, cigar = align_WFA(qryseq, refseq)
        else:
            LOGGER.error(f"Alignment method not recognized (method = {method})")
            sys.exit(1)

        nuc_vars = [
            x
            for x in self.extract_vars_from_cigar(
                qryseq, refseq, cigar, source_acc, data["cds_file"]
            )
        ]
        # empty string for parent_id row
        vars = "\n".join(["\t".join(x + ("",)) for x in nuc_vars])
        if nuc_vars:
            # create AA mutation
            aa_vars = "\n".join(
                ["\t".join(x) for x in self.lift_vars(nuc_vars, data["lift_file"])]
            )
            if aa_vars:
                # concatenate to the same file of NT variants
                vars += "\n" + aa_vars
            vars += "\n"
        try:
            with open(data["var_file"], "w") as handle:
                handle.write(
                    "#"
                    + "\t".join(
                        [
                            "id",
                            "ref",
                            "start",
                            "end",
                            "alt",
                            "accs",
                            "label",
                            "type",
                            "parent_id",
                        ]
                    )
                    + "\n"
                )
                handle.write(vars + "//")
        except OSError:
            os.makedirs(os.path.dirname(data["var_file"]), exist_ok=True)
            with open(data["var_file"], "w") as handle:
                handle.write(
                    "#"
                    + "\t".join(
                        [
                            "id",
                            "ref",
                            "start",
                            "end",
                            "alt",
                            "accs",
                            "label",
                            "type",
                            "parent_id",
                        ]
                    )
                    + "\n"
                )
                handle.write(vars + "//")
        return

    def extract_vars(self, qry_seq, ref_seq, elem_acc):
        """
        Note:
            Use element accession
            Add element type
            Frameshift is no longer used here
        """

        query_length = len(qry_seq)
        if query_length != len(ref_seq):
            sys.exit("error: sequences differ in length")
        qry_seq += " "
        ref_seq += " "
        i = 0
        offset = 0
        id_counter = count(1)  # Create an incremental counter starting from 1 (ID)

        while i < query_length:
            # match
            if qry_seq[i] == ref_seq[i]:
                pass
            # deletion
            elif qry_seq[i] == "-":
                s = i
                while qry_seq[i + 1] == "-":
                    i += 1
                start = s - offset
                end = i + 1 - offset
                if end - start == 1:
                    label = "del:" + str(start + 1)
                else:
                    label = "del:" + str(start + 1) + "-" + str(end)
                yield str(next(id_counter)), ref_seq[s : i + 1], str(start), str(
                    end
                ), " ", elem_acc, label, "nt"

            # insertion
            elif ref_seq[i] == "-":
                s = i - 1
                while ref_seq[i + 1] == "-":
                    i += 1
                # insertion at pos 0
                if s == -1:
                    ref = "."
                    alt = qry_seq[: i + 1]
                else:
                    ref = ref_seq[s]
                    alt = qry_seq[s : i + 1]
                pos = s - offset + 1
                yield str(next(id_counter)), ref, str(pos - 1), str(
                    pos
                ), alt, elem_acc, ref + str(pos) + alt, "nt"
                offset += i - s
            # snps
            else:
                ref = ref_seq[i]
                alt = qry_seq[i]
                pos = i - offset + 1
                yield str(next(id_counter)), ref, str(pos - 1), str(
                    pos
                ), alt, elem_acc, ref + str(pos) + alt, "nt"
            i += 1

    def translate(self, seq):
        """
        aa = []
        while len(seq) % 3 != 0:
            seq = seq[: len(seq) - 1]
        for codon in [seq[i : i + 3] for i in range(0, len(seq), 3)]:
            aa.append(tt[codon])
        return ("Our TT:","".join(aa))

        """
        _aa = ""
        try:
            if seq == "---":
                return "-"
            else:
                _aa = str(
                    Seq(seq.replace("-", "")).translate(table="Standard", to_stop=True)
                )
        except Exception as e:
            LOGGER.error("\n------- Fatal Error ---------")
            LOGGER.error("\nDebugging Information:")
            LOGGER.error(e)
            LOGGER.error("\n During translate:")
            LOGGER.error(seq)
            sys.exit(1)

        return _aa

    def lift_vars(  # noqa: C901
        self,
        nuc_vars: List[Tuple],
        df: pd.DataFrame,
    ) -> Generator[Tuple[str, str, str, str, str, str, str, str], None, None]:
        """
        Lift over nucleotide variants to protein (amino acid) variants.

        Parameters
        ----------
        nuc_vars:
            A list of tuples, where each tuple contains reference base,
                alternate base, start position, end position,
              frameshift indicator, and mutation label for each variant.
               exmaple [(1, 'G', '28680', '28681', 'K', 'MN908947.3', 'G28681K', 'nt'),
               (2, 'T', '28692', '28693', 'Y', 'MN908947.3', 'T28693Y', 'nt'),
               (3, 'G', '28880', '28881', 'A', 'MN908947.3', 'G28881A', 'nt')]
        df: pandas dataframe
            contain the original CDS position,NT and AA with respect to the reference.

        Yields
        -------
        Tuple
            A tuple containing
            ID AA_ref Start_pos END_pos AA_alt Reference   Label   Mutation_Type parentID
            4, H       39      40      X       QHD43422.1      H40X    cds  1
        """
        # updating the DF with alternate nucleotides (alt)
        # for positions specified in the nuc_var range.
        # ------------ this part of the code is the major problem that cause the slow performance

        # V.1 the original code version from covsonar1
        # for nuc_var in nuc_vars:
        #     if nuc_var[3] == ".":
        #         continue  # ignore uncovered terminal regions
        #     alt = "-" if nuc_var[3] == " " else nuc_var[3]
        #     start, end = map(int, (nuc_var[1], nuc_var[2]))
        #     for i in range(start, end):
        #         for j in range(1, 4):  # iterate over nucPos1, nucPos2, nucPos3
        #             col_name = f"alt{j}"
        #             df.loc[df[f"nucPos{j}"] == i, col_name] = alt

        # V.1.5 a little bit of improvement of code explainability (no performance improved)
        # for nuc_var in nuc_vars:
        #     if nuc_var[3] != ".":
        #         alt = "-" if nuc_var[3] == " " else nuc_var[3]
        #         start, end = map(int, (nuc_var[1], nuc_var[2]))
        #         positions = np.arange(start, end)
        #         mask = np.isin(df["nucPos1"], positions)
        #         df.loc[mask, "alt1"] = alt
        #         mask = np.isin(df["nucPos2"], positions)
        #         df.loc[mask, "alt2"] = alt
        #         mask = np.isin(df["nucPos3"], positions)
        #         df.loc[mask, "alt3"] = alt

        # Convert nuc_vars into a DataFrame to facilitate adding unique IDs
        nuc_vars_df = pd.DataFrame(
            nuc_vars,
            columns=["ID", "ref", "start", "end", "alt", "elem_acc", "label", "type"],
        )
        nuc_vars_df[["start", "end"]] = nuc_vars_df[["start", "end"]].astype(int)
        nuc_vars_df["ID"] = nuc_vars_df["ID"].astype(int)
        nuc_vars_df["parentID"] = nuc_vars_df[
            "ID"
        ]  # range(1, len(nuc_vars_df) + 1)  # Add unique IDs for NT variants
        # Start amino acid (AA) IDs after the last nucleotide (NT) ID
        next_aa_id = nuc_vars_df["ID"].max() + 1 if not nuc_vars_df.empty else 1

        # newer version
        nucPos1 = df["nucPos1"].to_numpy(dtype=np.int32)
        nucPos2 = df["nucPos2"].to_numpy(dtype=np.int32)
        nucPos3 = df["nucPos3"].to_numpy(dtype=np.int32)
        alt1 = df["alt1"].to_numpy()
        alt2 = df["alt2"].to_numpy()
        alt3 = df["alt3"].to_numpy()

        for nuc_var in nuc_vars:
            if nuc_var[3] != ".":
                alt = "-" if nuc_var[4] == " " else nuc_var[4]
                start, end = map(int, (nuc_var[2], nuc_var[3]))

                # Boolean indexing directly
                mask1 = (nucPos1 >= start) & (nucPos1 < end)
                mask2 = (nucPos2 >= start) & (nucPos2 < end)
                mask3 = (nucPos3 >= start) & (nucPos3 < end)

                alt1[mask1] = alt
                alt2[mask2] = alt
                alt3[mask3] = alt

        df["alt1"] = alt1
        df["alt2"] = alt2
        df["alt3"] = alt3
        # ------------------------------------------------------------
        # keep rows where there is a change in the nucleotide.
        # by dropping rows that dont get changed
        df.drop(
            df.loc[
                (df["ref1"] == df["alt1"])
                & (df["ref2"] == df["alt2"])
                & (df["ref3"] == df["alt3"])
            ].index,
            inplace=True,
        )

        if not df.empty:

            # translates the updated nucleotide positions
            # to amino acid changes using the translation table (tt)

            # df["altAa"] = df.apply(
            #     lambda x: self.translate(x["alt1"] + x["alt2"] + x["alt3"]), axis=1
            # )
            df["altAa"] = df["alt1"] + df["alt2"] + df["alt3"]
            df["altAa"] = df["altAa"].apply(
                lambda seq: (
                    "-"
                    if seq == "---"
                    else str(
                        Seq(seq.replace("-", "")).translate(
                            table="Standard", to_stop=True
                        )
                    )
                )
            )
            # get only rows where there is a change in amino acid.
            # by dropping rows that dont get changed
            df.drop(df[df["aa"] == df["altAa"]].index, inplace=True)

            # for snps or inserts
            for row in df.loc[(df["altAa"] != "-") & (df["altAa"] != "")].itertuples():
                pos = row.aaPos + 1
                label = row.aa + str(pos) + row.altAa
                # Match CDS variant to  NT variant
                matching_nt = nuc_vars_df[
                    (
                        (nuc_vars_df["start"] <= row.nucPos1)
                        & (nuc_vars_df["end"] > row.nucPos1)
                    )
                    | (
                        (nuc_vars_df["start"] <= row.nucPos2)
                        & (nuc_vars_df["end"] > row.nucPos2)
                    )
                    | (
                        (nuc_vars_df["start"] <= row.nucPos3)
                        & (nuc_vars_df["end"] > row.nucPos3)
                    )
                ]
                parent_id = (
                    ",".join(matching_nt["parentID"].astype(str))
                    if not matching_nt.empty
                    else ""
                )
                # 'id','ref','start', 'end', 'alt', 'accs', 'label', 'type', 'parent_id'
                yield str(next_aa_id), row.aa, str(pos - 1), str(pos), row.altAa, str(
                    row.accession
                ), label, "cds", parent_id
                next_aa_id += 1
            # frameshift?

            # for deletions
            # the prev_row will be used to calculate the deletion label larger
            prev_row = None
            for index, row in (
                df.loc[(df["altAa"] == "-")].sort_values(["elemid", "aaPos"]).iterrows()
            ):
                if prev_row is None:
                    # Initialize a new deletion block
                    prev_row = row
                elif prev_row["elemid"] == row["elemid"] and row["aaPos"] == prev_row[
                    "aaPos"
                ] + len(prev_row["aa"]):
                    # Extend the current deletion block
                    prev_row["aa"] += row["aa"]

                else:
                    # Finalize the previous deletion block
                    start = prev_row["aaPos"]
                    end = prev_row["aaPos"] + len(prev_row["aa"])
                    if end - start == 1:
                        label = "del:" + str(start + 1)
                    else:
                        label = "del:" + str(start + 1) + "-" + str(end)
                    # Match CDS variant to NT variant
                    matching_nt = nuc_vars_df[
                        (
                            (nuc_vars_df["start"] <= prev_row.nucPos1)
                            & (nuc_vars_df["end"] > prev_row.nucPos1)
                        )
                        | (
                            (nuc_vars_df["start"] <= prev_row.nucPos2)
                            & (nuc_vars_df["end"] > prev_row.nucPos2)
                        )
                        | (
                            (nuc_vars_df["start"] <= prev_row.nucPos3)
                            & (nuc_vars_df["end"] > prev_row.nucPos3)
                        )
                    ]
                    parent_id = (
                        ",".join(matching_nt["parentID"].astype(str))
                        if not matching_nt.empty
                        else ""
                    )
                    # 'id','ref','start', 'end', 'alt', 'accs', 'label', 'type', 'parent_id'
                    yield str(next_aa_id), prev_row["aa"], str(start), str(
                        end
                    ), " ", str(prev_row["accession"]), label, "cds", parent_id

                    # Start a new deletion block
                    prev_row = row
                    next_aa_id += 1

            # Yield the last aggregated deletion if it exists
            if prev_row is not None:
                start = prev_row["aaPos"]
                end = prev_row["aaPos"] + len(prev_row["aa"])
                if end - start == 1:
                    label = "del:" + str(start + 1)
                else:
                    label = "del:" + str(start + 1) + "-" + str(end)
                matching_nt = nuc_vars_df[
                    (
                        (nuc_vars_df["start"] <= prev_row.nucPos1)
                        & (nuc_vars_df["end"] > prev_row.nucPos1)
                    )
                    | (
                        (nuc_vars_df["start"] <= prev_row.nucPos2)
                        & (nuc_vars_df["end"] > prev_row.nucPos2)
                    )
                    | (
                        (nuc_vars_df["start"] <= prev_row.nucPos3)
                        & (nuc_vars_df["end"] > prev_row.nucPos3)
                    )
                ]
                # 'id','ref','start', 'end', 'alt', 'accs', 'label', 'type', 'parent_id'
                parent_id = (
                    ",".join(matching_nt["parentID"].astype(str))
                    if not matching_nt.empty
                    else ""
                )

                yield str(next_aa_id), prev_row["aa"], str(start), str(end), " ", str(
                    prev_row["accession"]
                ), label, "cds", parent_id
                next_aa_id += 1

    def extract_vars_from_cigar(  # noqa: C901
        self, qryseq, refseq, cigar, elemid, cds_file
    ):
        # get annotation for frameshift detection
        # cds_df = pd.read_pickle(cds_file)
        # cds_set = set(cds_df[cds_df["end"] == 0])

        # extract
        refpos = 0
        qrypos = 0
        qrylen = len(qryseq)
        prefix = False
        vars = []
        id_counter = count(1)  # Create an incremental counter starting from 1 (ID)

        for match in self.cigar_pattern.finditer(cigar):
            vartype = match.group(2)
            varlen = int(match.group(1))
            # identical sites
            if vartype == "=" or vartype == "M":
                refpos += varlen
                qrypos += varlen
            # snp handling
            elif vartype == "X":

                for x in range(varlen):
                    ref = refseq[refpos]
                    alt = qryseq[qrypos]

                    vars.append(
                        (
                            str(next(id_counter)),
                            ref,
                            str(refpos),
                            str(refpos + 1),
                            alt,
                            elemid,
                            ref + str(refpos + 1) + alt,
                            "nt",
                        )
                    )
                    refpos += 1
                    qrypos += 1
            # deletion handling
            elif vartype == "D":
                if (
                    refpos == 0 and prefix is False
                ) or qrypos == qrylen:  # deletion at sequence terminus
                    vars.append(
                        (
                            str(next(id_counter)),
                            refseq[refpos : refpos + varlen],
                            str(refpos),
                            str(refpos + varlen),
                            " ",
                            elemid,
                            "del:" + str(refpos + 1) + "-" + str(refpos + varlen),
                            "nt",
                        )
                    )
                    refpos += varlen
                elif varlen == 1:  # 1bp deletion

                    vars.append(
                        (
                            str(next(id_counter)),
                            refseq[refpos],
                            str(refpos),
                            str(refpos + 1),
                            " ",
                            elemid,
                            "del:" + str(refpos + 1),
                            "nt",
                            # self.detect_frameshifts(
                            #    refpos, refpos + 1, " ", cds_df, cds_set
                            # ),
                        )
                    )
                    refpos += 1
                else:  # multi-bp inner deletion

                    vars.append(
                        (
                            str(next(id_counter)),
                            refseq[refpos : refpos + varlen],
                            str(refpos),
                            str(refpos + varlen),
                            " ",
                            elemid,
                            "del:" + str(refpos + 1) + "-" + str(refpos + varlen),
                            "nt",
                            # self.detect_frameshifts(
                            #    refpos, refpos + varlen, " ", cds_df, cds_set
                            # ),
                        )
                    )
                    refpos += varlen
            # insertion handling
            elif vartype == "I":

                if refpos == 0:  # to consider insertion before sequence start
                    ref = "."
                    alt = qryseq[:varlen]
                    prefix = True
                    # fs = "0"
                else:
                    ref = refseq[refpos - 1]
                    alt = qryseq[qrypos - 1 : qrypos + varlen]
                    # fs = self.detect_frameshifts(
                    #     refpos - 1, refpos, alt, cds_df, cds_set
                    # )
                vars.append(
                    (
                        str(next(id_counter)),
                        ref,
                        str(refpos - 1),
                        str(refpos),
                        alt,
                        elemid,
                        ref + str(refpos) + alt,
                        "nt",
                        # fs,
                    )
                )
                qrypos += varlen
            # unknown
            else:
                sys.exit(
                    "error: Sonar cannot interpret '" + vartype + "' in cigar string."
                )
        return vars
