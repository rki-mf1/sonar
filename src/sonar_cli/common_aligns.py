import re
import sys

from Bio.Align.Applications import MafftCommandline
import parasail
from pywfa import WavefrontAligner
from sonar_cli.logging import LoggingConfigurator


# Initialize logger
LOGGER = LoggingConfigurator.get_logger()
cigar_pattern = re.compile(r"(\d+)(\D)")


def align_WFA(qryseq, refseq, gapopen=16, gapextend=4):
    """Method for WFA2-lib run"""
    # wavefront_aligner_attr_t attributes = wavefront_aligner_attr_default;
    # attributes.alignment_form.span = alignment_endsfree;
    # attributes.alignment_form.pattern_begin_free = 0;
    # attributes.alignment_form.pattern_end_free = 0;
    # attributes.alignment_form.text_begin_free = text_begin_free;
    # attributes.alignment_form.text_end_free = text_end_free;
    #
    # From WFA2-lib:
    # WFA2lib follows the convention that describes how to transform the (1) Pattern/Query into the (2) Text/Database/Reference used in classic pattern matching papers. However, the SAM CIGAR specification describes the transformation from (2) Reference to (1) Query. If you want CIGAR-compliant alignments, swap the pattern and text sequences argument when calling the WFA2lib's align functions (to convert all the Ds into Is and vice-versa).
    # so there is a chance that the query and ref (pattern and text in WFA language) need to be swapped
    a = WavefrontAligner(refseq, gap_opening=gapopen, gap_extension=gapextend)
    a.wavefront_align(qryseq)
    if a.status != 0:  # alignment was not successful
        LOGGER.error("An error occurred in align_WFA")
        LOGGER.error(f"Input sequence: {qryseq}")
        sys.exit("--stop--")
    cigar = a.cigarstring
    # res = a(qryseq)
    traceback_ref = ""  # res.aligned_pattern
    traceback_query = ""  # res.aligned_text
    return (
        traceback_ref,
        traceback_query,
        cigar,
    )


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
