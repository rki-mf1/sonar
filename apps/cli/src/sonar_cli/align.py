from collections import defaultdict
from itertools import count
import os
import re
import sys
import warnings

from Bio import BiopythonWarning
from Bio.Seq import Seq
import numpy as np
import pandas as pd
from sonar_cli.common_aligns import align_MAFFT
from sonar_cli.common_aligns import align_Parasail
from sonar_cli.common_utils import read_seqcache
from sonar_cli.config import TMP_CACHE
from sonar_cli.logging import LoggingConfigurator

warnings.simplefilter("ignore", BiopythonWarning)
# This will be the default in pandas >3.0 apparently. Should give performance
# improvements but for now we get errors.
# pd.options.mode.copy_on_write = True

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()


class sonarAligner:
    def __init__(self, cache_outdir=None, method=1, allow_updates=False, debug=False):
        self.nuc_profile = []
        self.nuc_n_profile = []
        self.aa_profile = []
        self.aa_n_profile = []
        self.cigar_pattern = re.compile(r"(\d+)(\D)")
        self.outdir = TMP_CACHE if not cache_outdir else os.path.abspath(cache_outdir)
        self.method = method
        self.allow_updates = allow_updates
        self.debug = debug

    def process_cached_sample(self, **sample_data: dict):
        if self.method == 1:
            # For alignment methods that return the reference and query
            # sequence strings as they would align to each other
            nuc_vars = self.process_cached_alignment(sample_data)
        elif self.method == 2 or self.method == 3:
            # For alignment methods that return a cigar string
            nuc_vars = self.process_cached_cigar(sample_data, self.method)

        # Convert nucleotide mutations to amino acid mutations
        aa_vars = self.nuc_to_aa_vars(nuc_vars, sample_data["lift_file"])
        # Create a table with both nucleotide and amino acid mutations
        all_vars = pd.concat([nuc_vars, aa_vars])

        if self.debug:
            os.makedirs(os.path.dirname(sample_data["var_file"]), exist_ok=True)
            all_vars.to_csv(sample_data["var_file"], sep="\t", index=False)

        # Write our var parquet file to be:
        # 1) used for the paranoid test
        # 2) sent to the backend for import
        os.makedirs(os.path.dirname(sample_data["var_parquet_file"]), exist_ok=True)
        all_vars.to_parquet(
            sample_data["var_parquet_file"],
            compression="zstd",
            compression_level=10,
            index=False,
        )

    def process_cached_alignment(self, data: dict):
        if not self.allow_updates:
            if not data["var_parquet_file"]:
                return True
            elif os.path.isfile(data["var_parquet_file"]):
                pd.read_parquet(data["var_parquet_file"])
                return True
        source_acc = str(data["source_acc"])

        # Do alignment
        alignment = align_MAFFT(data["seq_file"], data["ref_file"])
        # Extract nucleotide mutations from alignment
        nuc_vars = self.extract_nuc_vars_from_alignment(*alignment, elem_acc=source_acc)
        return nuc_vars

    def process_cached_cigar(self, data: dict, method: int):  # noqa: C901
        """
        Work with: Cigar format
        This function takes a sample file and processes it.
        create var file with NT and AA mutations
        """
        if not self.allow_updates:
            if data["var_parquet_file"] is None:
                return True
            elif os.path.isfile(data["var_parquet_file"]):
                pd.read_parquet(data["var_parquet_file"])
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

        nuc_vars = self.extract_nuc_vars_from_cigar(
            qryseq, refseq, cigar, source_acc, data["cds_file"]
        )
        return nuc_vars

    def extract_nuc_vars_from_alignment(
        self, qry_seq, ref_seq, elem_acc
    ) -> pd.DataFrame:
        """Given two aligned sequences, return a table with nt variants (snps and indels)"""
        query_length = len(qry_seq)
        if query_length != len(ref_seq):
            sys.exit("Error: aligned sequences differ in length")
        qry_seq += " "
        ref_seq += " "
        i = 0
        offset = 0
        id_counter = count(1)

        # Collect our nucleotide variants here. Each element should be a
        # dictionary with the following keys:
        # - id
        # - ref
        # - start
        # - end
        # - alt
        # - reference_acc
        # - label
        # - type
        # - parent_id (= id for nucleotides)
        nuc_vars = []

        while i < query_length:
            # match
            if qry_seq[i] == ref_seq[i]:
                i += 1
                continue
            # deletion
            elif qry_seq[i] == "-":
                s = i
                while qry_seq[i + 1] == "-":
                    i += 1
                start = s - offset
                end = i + 1 - offset
                if end - start == 1:
                    label = f"del:{start + 1}"
                else:
                    label = f"del:{start + 1}-{end}"
                ref = ref_seq[s : i + 1]
                alt = " "
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
                start = pos - 1
                end = pos
                label = f"{ref}{pos}{alt}"
                offset += i - s
            # snps
            else:
                ref = ref_seq[i]
                alt = qry_seq[i]
                pos = i - offset + 1
                start = pos - 1
                end = pos
                label = f"{ref}{pos}{alt}"

            idx = int(next(id_counter))
            nuc_vars.append(
                {
                    "id": idx,
                    "ref": ref,
                    "start": start,
                    "end": end,
                    "alt": alt,
                    "reference_acc": elem_acc,
                    "label": label,
                    "type": "nt",
                    "parent_id": str(idx),
                }
            )
            i += 1

        nuc_df = pd.DataFrame(nuc_vars)
        # FIXME: doesn't handle the case when there are zero mutations
        return nuc_df

    def nuc_to_aa_vars(  # noqa: C901
        self,
        nuc_vars: pd.DataFrame,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Given a set of nucleotide mutations, return the aa mutations they would cause

        Parameters
        ----------
        nuc_vars: pandas dataframe
              [(1, 'G', '28680', '28681', 'K', 'MN908947.3', 'G28681K', 'nt'),
               (2, 'T', '28692', '28693', 'Y', 'MN908947.3', 'T28693Y', 'nt'),
               (3, 'G', '28880', '28881', 'A', 'MN908947.3', 'G28881A', 'nt')]
        df: pandas dataframe with information about the reference transcripts
                "elemid",
                "nucPos1",
                "nucPos2",
                "nucPos3",
                "ref1",
                "ref2",
                "ref3",
                "alt1",
                "alt2",
                "alt3",
                "symbol",
                "accession",
                "aaPos",
                "aa",

        Yields
        -------
        Pandas DataFrame containing
            id ref start end alt reference_acc   label   type parent_id
            4  H      39  40   X    QHD43422.1    H40X    cds         1
        """

        aa_vars = []
        next_aa_id = nuc_vars["id"].max() + 1 if not nuc_vars.empty else 1

        # ------------------------------------------------------------
        # Inject mutations into the genes table
        df["parent_ids"] = ""
        nucPos1 = df["nucPos1"].to_numpy(dtype=np.int32)
        nucPos2 = df["nucPos2"].to_numpy(dtype=np.int32)
        nucPos3 = df["nucPos3"].to_numpy(dtype=np.int32)
        alt1 = df["alt1"].to_numpy()
        alt2 = df["alt2"].to_numpy()
        alt3 = df["alt3"].to_numpy()
        is_modified = np.full(df.shape[0], False)
        child_to_parent = defaultdict(list)

        for nuc_var in nuc_vars[nuc_vars["ref"].values != "."].itertuples():
            alt = "-" if nuc_var.alt == " " else nuc_var.alt
            id = nuc_var.id
            start = nuc_var.start
            end = nuc_var.end

            # Boolean indexing directly
            mask1 = (nucPos1 >= start) & (nucPos1 < end)
            mask2 = (nucPos2 >= start) & (nucPos2 < end)
            mask3 = (nucPos3 >= start) & (nucPos3 < end)

            alt1[mask1] = alt
            alt2[mask2] = alt
            alt3[mask3] = alt
            just_modified = mask1 | mask2 | mask3
            is_modified |= just_modified
            for child in np.flatnonzero(just_modified).tolist():
                child_to_parent[child].append(str(id))

        df["alt1"] = alt1
        df["alt2"] = alt2
        df["alt3"] = alt3
        df.loc[child_to_parent.keys(), "parent_ids"] = [
            ",".join(v) for v in child_to_parent.values()
        ]
        df = df.drop(df.index[~is_modified])

        # Actually calculate the aa mutations:
        if not df.empty:
            df["altAa"] = df["alt1"] + df["alt2"] + df["alt3"]
            df["altAa"] = df["altAa"].apply(
                lambda seq: (
                    str(
                        Seq(seq.replace("-", "")).translate(
                            table="Standard", to_stop=True, gap="-"
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
                parent_id = row.parent_ids
                aa_vars.append(
                    {
                        "id": int(next_aa_id),
                        "ref": row.aa,
                        "start": pos - 1,
                        "end": pos,
                        "alt": row.altAa,
                        "reference_acc": row.accession,
                        "label": label,
                        "type": "cds",
                        "parent_id": parent_id,
                    }
                )
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
                    aa_vars.append(
                        {
                            "id": int(next_aa_id),
                            "ref": prev_row.aa,
                            "start": start,
                            "end": end,
                            "alt": " ",
                            "reference_acc": prev_row.accession,
                            "label": label,
                            "type": "cds",
                            "parent_id": prev_row.parent_id,
                        }
                    )

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

                aa_vars.append(
                    {
                        "id": int(next_aa_id),
                        "ref": prev_row.aa,
                        "start": start,
                        "end": end,
                        "alt": " ",
                        "reference_acc": prev_row.accession,
                        "label": label,
                        "type": "cds",
                        "parent_id": parent_id,
                    }
                )
                next_aa_id += 1

        return pd.DataFrame(aa_vars)

    def extract_nuc_vars_from_cigar(  # noqa: C901
        self, qryseq, refseq, cigar, elemid, cds_file
    ):
        refpos = 0
        qrypos = 0
        id_counter = count(1)
        nuc_vars = []

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
                    start = refpos
                    end = refpos + 1
                    label = f"{ref}{end}{alt}"
                    idx = int(next(id_counter))
                    nuc_vars.append(
                        {
                            "id": idx,
                            "ref": ref,
                            "start": start,
                            "end": end,
                            "alt": alt,
                            "reference_acc": elemid,
                            "label": label,
                            "type": "nt",
                            "parent_id": str(idx),
                        }
                    )
                    refpos += 1
                    qrypos += 1
            # deletion handling
            elif vartype == "D":
                ref = refseq[refpos : refpos + varlen]
                start = refpos
                end = refpos + varlen
                alt = " "
                if varlen == 1:
                    label = f"del:{end}"
                else:
                    label = f"del:{start + 1}-{end}"
                idx = int(next(id_counter))
                nuc_vars.append(
                    {
                        "id": idx,
                        "ref": ref,
                        "start": start,
                        "end": end,
                        "alt": alt,
                        "reference_acc": elemid,
                        "label": label,
                        "type": "nt",
                        "parent_id": str(idx),
                    }
                )
                refpos += varlen

            # insertion handling
            elif vartype == "I":
                start = refpos - 1
                end = refpos
                if refpos == 0:
                    # insertion before sequence start
                    ref = "."
                    alt = qryseq[:varlen]
                else:
                    ref = refseq[refpos - 1]
                    alt = qryseq[qrypos - 1 : qrypos + varlen]
                label = f"{ref}{refpos}{alt}"
                idx = int(next(id_counter))
                nuc_vars.append(
                    {
                        "id": idx,
                        "ref": ref,
                        "start": start,
                        "end": end,
                        "alt": alt,
                        "reference_acc": elemid,
                        "label": label,
                        "type": "nt",
                        "parent_id": str(idx),
                    }
                )
                qrypos += varlen
            # unknown
            else:
                sys.exit(
                    "error: Sonar cannot interpret '" + vartype + "' in cigar string."
                )
        nuc_df = pd.DataFrame(nuc_vars)
        # FIXME: doesn't handle the case when there are zero mutations
        return nuc_df
