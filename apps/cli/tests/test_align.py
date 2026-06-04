import pandas as pd
from sonar_cli.align import sonarAligner


def test_nuc_to_aa_vars_stop_gain_substitution(tmp_path):
    """
    Regression test for issue #559 (under-translation of stop-gain substitutions).

    A substitution that turns a sense codon into a stop codon (e.g. ORF8:Q27*,
    CAA -> TAA) must be reported as a "*" amino-acid change.

    The bug: ``Seq(codon).translate(..., to_stop=True)`` truncates at the stop
    codon and returns "" for a codon that *is* a stop. The substitution emit loop
    filters out ``altAa == ""``, so the stop-gain mutation was silently dropped
    (0% call rate vs ~100% in NextClade). Using ``to_stop=False`` yields "*" so
    the mutation is reported.
    """
    aligner = sonarAligner(cache_outdir=str(tmp_path))

    # SNP C->T at the first nucleotide of the Q codon: CAA (Q) -> TAA (stop).
    nuc_vars = pd.DataFrame(
        [
            {
                "id": 1,
                "ref": "C",
                "start": 27915,
                "end": 27916,
                "alt": "T",
                "reference_acc": "MN908947.3",
                "label": "C27916T",
                "type": "nt",
                "frameshift": 0,
                "parent_id": "1",
            }
        ]
    )

    lift_df = pd.DataFrame(
        [
            {
                "elemid": 1,
                "nucPos1": 27915,
                "nucPos2": 27916,
                "nucPos3": 27917,
                "ref1": "C",
                "ref2": "A",
                "ref3": "A",
                "alt1": "C",
                "alt2": "A",
                "alt3": "A",
                "symbol": "ORF8",
                "accession": "QHD43422.10",
                "aaPos": 26,
                "aa": "Q",
            }
        ]
    )

    aa_vars = aligner.nuc_to_aa_vars(nuc_vars, lift_df)

    assert len(aa_vars) == 1, (
        "Stop-gain substitution must be reported, not dropped. "
        f"Got {len(aa_vars)} rows:\n{aa_vars}"
    )
    row = aa_vars.iloc[0]
    assert row["alt"] == "*", f"Expected stop '*', got '{row['alt']}'"
    assert row["label"] == "Q27*", f"Expected label 'Q27*', got '{row['label']}'"


def test_nuc_to_aa_vars_non_codon_aligned_deletion(tmp_path):
    """
    Regression test for issue #552: a non-codon-aligned in-frame deletion
    where the trailing boundary codon has only its first nucleotide (alt1)
    inside the deleted range.

    del:21765-21770 (1-based, 6 nt = 2 AAs) should yield S:del:69-70.

    Note: aaPos in the lift DataFrame is 0-indexed; the deletion label is
    1-indexed (label = f"del:{aaPos+1}-{aaPos+len(aa)}"). So aaPos=68
    corresponds to amino acid 69 and aaPos=69 corresponds to amino acid 70.

    Codons involved (nucPos values are 0-based):
      aaPos=67 (H, AA 68 in 1-based): nucPos1=21763, nucPos2=21764, nucPos3=21765
        → nucPos2 and nucPos3 fall in the deletion range, but NOT nucPos1;
          this codon is partially deleted and must NOT appear in the output.
      aaPos=68 (H, AA 69 in 1-based): nucPos1=21766, nucPos2=21767, nucPos3=21768
        → all three positions deleted → altAa=="---" → treated as deletion.
      aaPos=69 (V, AA 70 in 1-based): nucPos1=21769, nucPos2=21770, nucPos3=21771
        → only nucPos1 falls inside the range → alt1=="-" (trailing boundary
          codon); the fix ensures this is also treated as deletion.

    Without the fix (checking only altAa=="---"), aaPos=69 is silently dropped
    and the output is an incorrect single-AA deletion instead of del:69-70.
    """
    aligner = sonarAligner(cache_outdir=str(tmp_path))

    # Nucleotide deletion: del:21765-21770 (1-based) → start=21764, end=21770 (0-based half-open).
    # A single space " " in the alt column is the codebase convention for deletions;
    # nuc_to_aa_vars converts it to "-" internally.
    nuc_vars = pd.DataFrame(
        [
            {
                "id": 1,
                "ref": "CATCAT",
                "start": 21764,
                "end": 21770,
                "alt": " ",
                "reference_acc": "MN908947.3",
                "label": "del:21765-21770",
                "type": "nt",
                "frameshift": 0,
                "parent_id": "1",
            }
        ]
    )

    # Minimal lift DataFrame for the three codons surrounding the deletion.
    # alt1/alt2/alt3 start equal to ref1/ref2/ref3 (reference state before mutation).
    # CAT encodes H (histidine); GTC encodes V (valine).
    lift_df = pd.DataFrame(
        [
            {
                "elemid": 1,
                "nucPos1": 21763,
                "nucPos2": 21764,
                "nucPos3": 21765,
                "ref1": "C",
                "ref2": "A",
                "ref3": "T",
                "alt1": "C",
                "alt2": "A",
                "alt3": "T",
                "symbol": "S",
                "accession": "QHD43422.1",
                "aaPos": 67,
                "aa": "H",
            },
            {
                "elemid": 1,
                "nucPos1": 21766,
                "nucPos2": 21767,
                "nucPos3": 21768,
                "ref1": "C",
                "ref2": "A",
                "ref3": "T",
                "alt1": "C",
                "alt2": "A",
                "alt3": "T",
                "symbol": "S",
                "accession": "QHD43422.1",
                "aaPos": 68,
                "aa": "H",
            },
            {
                "elemid": 1,
                "nucPos1": 21769,
                "nucPos2": 21770,
                "nucPos3": 21771,
                "ref1": "G",
                "ref2": "T",
                "ref3": "C",
                "alt1": "G",
                "alt2": "T",
                "alt3": "C",
                "symbol": "S",
                "accession": "QHD43422.1",
                "aaPos": 69,
                "aa": "V",
            },
        ]
    )

    aa_vars = aligner.nuc_to_aa_vars(nuc_vars, lift_df)

    # Exactly one CDS deletion must be emitted, spanning both aaPos=68 and aaPos=69
    # (amino acids 69 and 70 in 1-based notation → label "del:69-70").
    del_rows = aa_vars[aa_vars["alt"] == " "]
    assert len(del_rows) == 1, (
        f"Expected 1 deletion record, got {len(del_rows)}. " f"Full aa_vars:\n{aa_vars}"
    )
    row = del_rows.iloc[0]
    assert (
        row["label"] == "del:69-70"
    ), f"Expected label 'del:69-70', got '{row['label']}'"
    assert row["reference_acc"] == "QHD43422.1"
    assert row["type"] == "cds"
    assert row["start"] == 68
    assert row["end"] == 70
