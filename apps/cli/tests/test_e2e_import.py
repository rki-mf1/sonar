from pathlib import Path

import pytest

from .conftest import run_cli


# test gene bank import different viruses
@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(1)
def test_add_cov19_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/sars-cov-2/MN908947.nextclade.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(1)
def test_add_mpox_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/mpox/NC_063383.1.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(1)
def test_add_rsv_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/RSV/AF013254.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(1)
def test_add_measels_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/morbillivirus-hominis/NC_001498.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(1)
def test_add_hiv_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/HIV/AF033819.3.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(1)
def test_add_dengue_type2_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/dengue/type_2/NC_001474.2.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(1)
def test_add_ebola_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/ebola/NC_002549.1.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(1)
def test_add_zika_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/zika/NC_035889.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


# test data import
@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(2)
def test_parasail_no_anno_no_upload(monkeypatch, api_url, tmpfile_name):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 2 --fasta ../../../test-data/sars-cov-2/seqs.fasta.gz --cache {tmpfile_name}/parasail -t 2 --no-upload --must-pass-paranoid"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(3)
def test_mafft_no_anno_no_upload(monkeypatch, api_url, tmpfile_name):
    """Test import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/sars-cov-2/seqs.fasta.gz --cache {tmpfile_name}/mafft -t 2 --no-upload --must-pass-paranoid"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(4)
def test_add_sequence_mafft_anno_prop(monkeypatch, api_url, tmpfile_name):
    """Test import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    # monkeypatch.setattr(
    #     "mpire.WorkerPool.map_unordered",
    #     lambda self, func, args=(), progress_bar=True, progress_bar_options={}, kwds={}, callback=None, error_callback=None: (
    #         func(** arg) for arg in args
    #     ),
    # )
    command = f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/sars-cov-2/seqs.fasta.gz --cache {tmpfile_name}/mafft -t 2 --auto-anno --tsv sars-cov-2/meta.tsv --cols name=IMS_ID collection_date=DATE_DRAW sequencing_tech=SEQ_REASON sample_type=SAMPLE_TYPE --must-pass-paranoid"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(5)
def test_add_sequence_mafft_no_skip(monkeypatch, api_url, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    code = run_cli(
        f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/sars-cov-2/seqs.fasta.gz --cache {tmpfile_name}/mafft  --no-skip --no-upload --must-pass-paranoid"
    )
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(6)
def test_add_sequence_mafft_skip(monkeypatch, api_url, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    code = run_cli(
        f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/sars-cov-2/seqs.fasta.gz --cache {tmpfile_name}/mafft -t 1 --no-upload --must-pass-paranoid"
    )
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(7)
def test_mafft_anno_upload_rsv(monkeypatch, api_url, tmpfile_name):
    """Test rsv sample import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r AF013254.1 --method 1 --fasta ../../../test-data/RSV/RSV_20.fasta.xz --cache {tmpfile_name}/mafft -t 2 --skip-nx --must-pass-paranoid"
    code = run_cli(command)
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(8)
def test_mafft_anno_upload_mpox(monkeypatch, api_url, tmpfile_name):
    """Test rsv sample import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r NC_063383.1 --method 1 --fasta ../../../test-data/mpox/mpox_2.fasta.xz --cache {tmpfile_name}/mafft -t 2 --skip-nx --must-pass-paranoid"
    code = run_cli(command)
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(9)
def test_mafft_anno_upload_ebola(monkeypatch, api_url, tmpfile_name):
    """Test rsv sample import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r NC_002549.1 --method 1 --fasta ../../../test-data/ebola/ebola_20.fasta.xz --cache {tmpfile_name}/mafft -t 2 --skip-nx --must-pass-paranoid"
    code = run_cli(command)
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(10)
def test_mafft_anno_upload_dengue_type2(monkeypatch, api_url, tmpfile_name):
    """Test rsv sample import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r NC_001474.2 --method 1 --fasta ../../../test-data/dengue/type_2/dengue_type2_complete_13.fasta.xz --cache {tmpfile_name}/mafft -t 2 --skip-nx --must-pass-paranoid"
    code = run_cli(command)
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(11)
def test_mafft_anno_upload_hiv(monkeypatch, api_url, tmpfile_name):
    """Test rsv sample import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.imap_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(**arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r AF033819.3 --method 1 --fasta ../../../test-data/HIV/HIV_20.fasta.xz --cache {tmpfile_name}/mafft -t 2 --skip-nx --must-pass-paranoid"
    code = run_cli(command)
    assert code == 0


# @pytest.mark.xdist_group(name="group1")
# @pytest.mark.order(7)
# def test_wfa_anno_no_upload(monkeypatch, api_url, tmpfile_name):
#     """Test import command using wfa method"""
#     monkeypatch.chdir(Path(__file__).parent)
#     monkeypatch.setattr(
#         "mpire.WorkerPool.imap_unordered",
#         lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
#             func(**arg) for arg in args
#         ),
#     )
#     command = f"import --db {api_url} -r MN908947.3 --method 3 --fasta ../../../test-data/sars-cov-2/seqs.fasta.gz --cache {tmpfile_name}/wfa -t 2 --no-upload"
#     code = run_cli(command)

#     assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(12)
def test_add_prop_autolink(monkeypatch, api_url, tmpfile_name):
    """Test import command using autolink"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.map_unordered",
        lambda self, func, args=(), progress_bar=True, progress_bar_options={}, kwds={}, callback=None, error_callback=None: (
            func(arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 1 --cache {tmpfile_name}/mafft -t 1  --tsv sars-cov-2/meta.tsv --cols name=IMS_ID --auto-link"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(13)
def test_add_prop(monkeypatch, api_url, tmpfile_name):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.map_unordered",
        lambda self, func, args=(), progress_bar=True, progress_bar_options={}, kwds={}, callback=None, error_callback=None: (
            func(arg) for arg in args
        ),
    )
    command = f"import --db {api_url} -r MN908947.3 --method 1 --cache {tmpfile_name}/mafft -t 2 --tsv sars-cov-2/meta.tsv --cols name=IMS_ID collection_date=DATE_DRAW sequencing_tech=SEQ_REASON sample_type=SAMPLE_TYPE"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group3")
@pytest.mark.order(1)
def test_add_influ_gbk(monkeypatch, capfd, api_url):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)
    # multiple segments  join with 1 whitespace
    new_ref_file = "../../../test-data/influenza/H1N1/NC_026438_seg1.gb"
    new_ref_file += " ../../../test-data/influenza/H1N1/NC_026435_seg2.gb"
    new_ref_file += " ../../../test-data/influenza/H1N1/NC_026437_seg3.gb"
    new_ref_file += " ../../../test-data/influenza/H1N1/NC_026433_seg4.gb"
    new_ref_file += " ../../../test-data/influenza/H1N1/NC_026436_seg5.gb"
    new_ref_file += " ../../../test-data/influenza/H1N1/NC_026434_seg6.gb"
    new_ref_file += " ../../../test-data/influenza/H1N1/NC_026431_seg7.gb"
    new_ref_file += " ../../../test-data/influenza/H1N1/NC_026432_seg8.gb"

    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group3")
@pytest.mark.order(2)
def test_add_influ_segment(monkeypatch, api_url, tmpfile_name):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)
    command = f"import --db {api_url} -r NC_026438.1 --method 1 --fasta ../../../test-data/influenza/H1N1/H1N1.sequences.fasta.xz --cache {tmpfile_name}/mafft_influ -t 2 --auto-anno"
    code = run_cli(command)

    assert code == 0
