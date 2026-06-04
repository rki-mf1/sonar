import glob
import multiprocessing as mp
import os

import pandas as pd
import pytest
from sonar_cli.align import sonarAligner


def _write_parquet_to(path, df):
    """Top-level worker (must be picklable for the 'spawn'/'fork' pool) that
    writes ``df`` to ``path`` via the aligner's atomic-write helper."""
    sonarAligner._atomic_write(
        path,
        lambda p: df.to_parquet(
            p, compression="zstd", compression_level=10, index=False
        ),
    )


def test_atomic_write_produces_valid_parquet_and_no_temp_leftovers(tmp_path):
    """Regression test for issue #557.

    The atomic-write helper must produce a complete, readable Parquet file and
    leave no ``.tmp`` files behind in the target directory.
    """
    out_dir = tmp_path / "var" / "ab"
    target = str(out_dir / "sample.var.parquet")
    df = pd.DataFrame({"ref": ["A", "C"], "alt": ["T", "G"], "start": [1, 2]})

    _write_parquet_to(target, df)

    # The published file is a complete, readable Parquet file.
    assert os.path.isfile(target)
    pd.testing.assert_frame_equal(pd.read_parquet(target), df)
    # No stray temp files remain in the target directory.
    assert glob.glob(os.path.join(str(out_dir), "*.tmp")) == []


def test_atomic_write_cleans_up_on_failure(tmp_path):
    """If the write callback raises, no temp file is left and the original
    target (if any) is untouched."""
    out_dir = tmp_path / "var"
    target = str(out_dir / "sample.var.parquet")

    def boom(_path):
        raise ValueError("write failed")

    with pytest.raises(ValueError, match="write failed"):
        sonarAligner._atomic_write(target, boom)

    assert not os.path.exists(target)
    assert glob.glob(os.path.join(str(out_dir), "*.tmp")) == []


def test_atomic_write_concurrent_same_path_stays_valid(tmp_path):
    """Multiple processes writing the SAME path concurrently (the issue #557
    scenario: duplicate sequences sharing one var_parquet_file) must always
    leave a complete, readable Parquet file — never a truncated/corrupt one."""
    out_dir = tmp_path / "var" / "cd"
    target = str(out_dir / "shared.var.parquet")
    # A non-trivial frame so a torn write would be detectable.
    df = pd.DataFrame(
        {
            "ref": ["A", "C", "G", "T"] * 250,
            "alt": ["T", "G", "C", "A"] * 250,
            "start": list(range(1000)),
        }
    )

    ctx = mp.get_context("fork")
    procs = [ctx.Process(target=_write_parquet_to, args=(target, df)) for _ in range(8)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
        assert p.exitcode == 0

    # The final file is complete and readable despite the concurrent races.
    pd.testing.assert_frame_equal(pd.read_parquet(target), df)
    assert glob.glob(os.path.join(str(out_dir), "*.tmp")) == []


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
