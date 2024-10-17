import re
import sys

from Bio.Align.Applications import MafftCommandline
import parasail
from pywfa import cigartuples_to_str
from pywfa import WavefrontAligner
from sonar_cli.logging import LoggingConfigurator


# Initialize logger
LOGGER = LoggingConfigurator.get_logger()
cigar_pattern = re.compile(r"(\d+)(\D)")


def align_WFA(qryseq, refseq, gapopen=6, gapextend=1):
    """Method for WFA2-lib run"""
    # Scoring settings from Nextclade source code (https://github.com/nextstrain/nextclade/blob/master/packages/nextclade/src/align/params.rs#L156)
    # penalty_gap_extend: 0,
    # penalty_gap_open: 6,
    # penalty_gap_open_in_frame: 7,
    # penalty_gap_open_out_of_frame: 8,
    # penalty_mismatch: 1,
    # score_match: 3,
    match = -3
    mismatch = 1
    left_align_indels = True
    try:
        # WFA2-lib right aligns indels by default. To force left alignment we reverse our sequences before doing alignment.
        # See: https://github.com/smarco/WFA2-lib/issues/37
        if left_align_indels:
            refseq = refseq[::-1]
            qryseq = qryseq[::-1]

        reference_length = len(refseq)
        a = WavefrontAligner(
            refseq,
            match=match,
            mismatch=mismatch,
            gap_opening=gapopen,
            gap_extension=gapextend,
            span="ends-free",
            distance="affine",
            pattern_begin_free=reference_length,
            pattern_end_free=reference_length,
            text_begin_free=0,
            text_end_free=0,
            wildcard="N",
        )
        alignment = a(qryseq)
        if alignment.status != 0:  # alignment was not successful
            LOGGER.error("An error occurred in align_WFA")
            if left_align_indels:
                qryseq = qryseq[::-1]
            LOGGER.error(f"Input sequence: {qryseq}")
            sys.exit("--stop--")

        cigartuple = alignment.cigartuples
        # Change wildcard positions to a mismatch in the cigar string
        cigartuple = wfa_cigar_n_match_to_mismatch(refseq, qryseq, cigartuple)
        if left_align_indels:
            cigartuple = cigartuple[::-1]
        cigar = cigartuples_to_str(cigartuple)

        # We don't use the traceback, we can just return empty strings here
        traceback_ref = ""
        traceback_query = ""

    except Exception as e:
        LOGGER.error(f"An error occurred in align_WFA: {e}")
        LOGGER.error(f"Input seq: {align_WFA}")
        sys.exit("--stop--")

    return (
        traceback_ref,
        traceback_query,
        cigar,
    )


def wfa_cigar_n_match_to_mismatch(ref, query, cigar_ops):
    """Helper method for pywfa, to change N from being a match to a mismatch in cigar strings"""
    # pywfa's wildcard argument correctly doesn't penalize ambiguous nucleotides (N), but it incorrectly calls them matches in the resulting cigar string. This function changes all positions with an N inside mathces into mismatches.
    CIGAR_OP_MATCH = [0, 7]
    CIGAR_OP_INSERT = 2
    CIGAR_OP_MISMATCH = 8
    qry_pos = 0
    cigar_ops_new = []

    for cigar_op in cigar_ops:
        operation = cigar_op[0]
        op_length = cigar_op[1]
        query_subseq = query[qry_pos : qry_pos + op_length]

        # We only do something special if there is an 'N' character in a match region
        if operation in CIGAR_OP_MATCH and "N" in query_subseq:
            last_match_end = 0
            for match in re.finditer("N+", query_subseq):
                # If there is anything before the match, create a new op and keep it as a match
                if last_match_end < match.start():
                    cigar_ops_new.append((operation, match.start() - last_match_end))
                # Create an op for the "N" region, setting it to be a mismatch
                cigar_ops_new.append((CIGAR_OP_MISMATCH, match.end() - match.start()))
                last_match_end = match.end()

            # If the match doesn't end in an N, add the remaining match operation.
            if last_match_end < op_length:
                cigar_ops_new.append((operation, op_length - last_match_end))

            qry_pos += op_length

        else:
            cigar_ops_new.append(cigar_op)
            if operation != CIGAR_OP_INSERT:
                qry_pos += op_length

    return cigar_ops_new


# gapopen=16, gapextend=4
# gapopen=10, gapextend=1
def align_Parasail(qryseq, refseq, gapopen=16, gapextend=4):
    """Method for parasail run"""
    result = parasail.sg_trace(qryseq, refseq, gapopen, gapextend, parasail.blosum62)
    return (
        result.traceback.ref,
        result.traceback.query,
        result.get_cigar().decode.decode(),
    )


def align_MAFFT(input_fasta):

    try:
        mafft_exe = "mafft"
        mafft_cline = MafftCommandline(
            mafft_exe, input=input_fasta, inputorder=True, auto=True
        )
        stdout, stderr = mafft_cline()
        # find the fist position of '\n' to get seq1
        s1 = stdout.find("\n") + 1
        # find the start of second sequence position
        e = stdout[1:].find(">") + 1
        # find the '\n' of the second sequence to get seq2
        s2 = stdout[e:].find("\n") + e
        ref = stdout[s1:e].replace("\n", "").upper()
        qry = stdout[s2:].replace("\n", "").upper()
    except Exception as e:
        LOGGER.error(f"An error occurred in align_MAFFT: {e}")
        LOGGER.error(f"Input filename: {input_fasta}")
        sys.exit("--stop--")
    return qry, ref


# Uncomment this if needed
# def align_Stretcher(qry, ref, gapopen=16, gapextend=4):
#     """Method for handling emboss stretcher run

#     Return:
#     """
#     try:
#         cline = StretcherCommandline(
#             asequence=qry,
#             bsequence=ref,
#             gapopen=gapopen,
#             gapextend=gapextend,
#             outfile="stdout",
#             aformat="fasta",
#             # datafile="EDNAFULL", auto set by strecher
#         )
#         stdout, stderr = cline()
#         # self.cal_seq_length(stdout[0:20], msg="stdout")
#         # find the fist position of '\n' to get seq1
#         s1 = stdout.find("\n") + 1
#         # find the start of second sequence position
#         e = stdout[1:].find(">") + 1
#         # find the '\n' of the second sequence to get seq2
#         s2 = stdout[e:].find("\n") + e
#         qry = stdout[s1:e].replace("\n", "")
#         ref = stdout[s2:].replace("\n", "")
#         # self.cal_seq_length(qry, msg="qry")
#         # self.cal_seq_length(ref, msg="ref")
#     except Exception:
#         try:
#             for proc in psutil.process_iter():
#                 # Get process name & pid from process object.
#                 processName = proc.name()
#                 processID = proc.pid
#                 if (
#                     "stretcher" in processName or "stretcher" in proc.cmdline()
#                 ):  # adapt this line to your needs
#                     LOGGER.info(
#                         f"Kill {processName}[{processID}] : {''.join(proc.cmdline())})"
#                     )
#                     proc.terminate()
#                     proc.kill()
#         except psutil.NoSuchProcess:
#             pass
#         LOGGER.error(
#             "Stop process during alignment; to rerun again, you may need to provide a new cache directory."
#         )
#         sys.exit("exited after ctrl-c")

#     return qry, ref

# Uncomment this if needed
# def gen_cigar(ref, qry):
#     if len(ref) != len(qry):
#         raise Exception("unequal length")
#     cigar = []
#     for i in range(len(ref)):
#         r, q = ref[i], qry[i]
#         if r == "-" and q == "-":
#             raise Exception("both gaps")
#         op = "=" if r == q else "I" if r == "-" else "D" if q == "-" else "X"
#         if len(cigar) > 0 and cigar[-1][1] == op:  # add to the last operation
#             cigar[-1][0] += 1
#         else:
#             cigar.append([1, op])
#             # a new operation
#     return "".join(map(lambda x: str(x[0]) + x[1], cigar))
#     # turn to string
