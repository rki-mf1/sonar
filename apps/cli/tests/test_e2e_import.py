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


@pytest.mark.xdist_group(name="group2")
@pytest.mark.order(1)
def test_add_mpox_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/mpox/clade-IIb-NC_063383.1.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group3")
@pytest.mark.order(1)
def test_add_rsv_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/RSV/RSV-B/OP975389.1.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group4")
@pytest.mark.order(1)
def test_add_measels_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/morbillivirus-hominis/NC_001498.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group5")
@pytest.mark.order(1)
def test_add_hiv_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/HIV/NC_001802.1.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group6")
@pytest.mark.order(1)
def test_add_dengue_type2_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/dengue/type_2/NC_001474.2.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group7")
@pytest.mark.order(1)
def test_add_ebola_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/ebola/NC_002549.1.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group8")
@pytest.mark.order(1)
def test_add_zika_ref(monkeypatch, capfd, api_url):
    monkeypatch.chdir(Path(__file__).parent)
    new_ref_file = "../../../test-data/zika/NC_035889.gb"
    code = run_cli(f" add-ref --db {api_url} --gb {new_ref_file} ")
    out, err = capfd.readouterr()
    assert "successfully." in err
    assert code == 0


@pytest.mark.xdist_group(name="group9")
@pytest.mark.order(1)
def test_add_influ_gbk(monkeypatch, capfd, api_url):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)
    # multiple segments  join with 1 whitespace
    new_ref_file = "../../../test-data/influenza/influenza-A/H1N1PDM_California/segment_1_NC_026438.1.gb"
    new_ref_file += " ../../../test-data/influenza/influenza-A/H1N1PDM_California/segment_2_NC_026435.1.gb"
    new_ref_file += " ../../../test-data/influenza/influenza-A/H1N1PDM_California/segment_3_NC_026437.1.gb"
    new_ref_file += " ../../../test-data/influenza/influenza-A/H1N1PDM_California/segment_4_CY121680.1.gb"
    new_ref_file += " ../../../test-data/influenza/influenza-A/H1N1PDM_California/segment_5_NC_026436.1.gb"
    new_ref_file += " ../../../test-data/influenza/influenza-A/H1N1PDM_California/segment_6_NC_026434.gb"
    new_ref_file += " ../../../test-data/influenza/influenza-A/H1N1PDM_California/segment_7_NC_026431.gb"
    new_ref_file += " ../../../test-data/influenza/influenza-A/H1N1PDM_California/segment_8_NC_026432.1.gb"

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
    command = f"import --db {api_url} -r MN908947.3 --method 2 --fasta ../../../test-data/sars-cov-2/SARS-CoV-2_6.fasta.gz --cache {tmpfile_name}/parasail -t 2 --no-upload --must-pass-paranoid"
    try:
        code = run_cli(command)
    except SystemExit as e:
        code = e.code
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(3)
def test_mafft_no_anno_no_upload(monkeypatch, api_url, tmpfile_name):
    """Test import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    command = f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/sars-cov-2/SARS-CoV-2_6.fasta.gz --cache {tmpfile_name}/mafft -t 2 --no-upload --must-pass-paranoid"
    try:
        code = run_cli(command)
    except SystemExit as e:
        code = e.code
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
    command = f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/sars-cov-2/SARS-CoV-2_6.fasta.gz --cache {tmpfile_name}/mafft -t 2 --auto-anno --tsv ../../../test-data/sars-cov-2/SARS-CoV-2_6.tsv --cols name=IMS_ID collection_date=DATE_DRAW sequencing_tech=SEQ_REASON sample_type=SAMPLE_TYPE --must-pass-paranoid"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(5)
def test_add_sequence_mafft_no_skip(monkeypatch, api_url, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)

    code = run_cli(
        f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/sars-cov-2/SARS-CoV-2_6.fasta.gz --cache {tmpfile_name}/mafft  --no-skip --no-upload --must-pass-paranoid"
    )
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(6)
def test_add_sequence_mafft_skip(monkeypatch, api_url, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)

    code = run_cli(
        f"import --db {api_url} -r MN908947.3 --method 1 --fasta ../../../test-data/sars-cov-2/SARS-CoV-2_6.fasta.gz --cache {tmpfile_name}/mafft -t 1 --no-upload --must-pass-paranoid"
    )
    assert code == 0


@pytest.mark.xdist_group(name="group3")
@pytest.mark.order(2)
def test_mafft_anno_upload_rsv(monkeypatch, api_url, tmpfile_name):
    """Test rsv sequence import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)

    command = f"import --db {api_url} -r OP975389.1 --method 1 --fasta ../../../test-data/RSV/RSV_20.fasta.xz --cache {tmpfile_name}/mafft -t 2 --skip-nx --must-pass-paranoid"
    code = run_cli(command)
    assert code == 0


@pytest.mark.xdist_group(name="group3")
@pytest.mark.order(3)
def test_add_rsv_samples(monkeypatch, api_url, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)
    command = f"import --db {api_url} -r OP975389.1 --tsv ../../../test-data/RSV/RSV_20.tsv --cache {tmpfile_name}/mafft --cols name=name"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group2")
@pytest.mark.order(2)
def test_mafft_anno_upload_mpox(monkeypatch, api_url, tmpfile_name):
    """Test mpox sequence import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)

    command_import = f"import --db {api_url} -r NC_063383.1 --method 1 --fasta ../../../test-data/mpox/mpox_2.fasta.xz --cache {tmpfile_name}/mafft -t 2 --skip-nx --must-pass-paranoid"
    code = run_cli(command_import)
    command_samples = f"import --db {api_url} -r NC_063383.1 --tsv ../../../test-data/mpox/mpox_2.tsv --cache {tmpfile_name}/mafft --cols name=name"
    code = run_cli(command_samples)
    assert code == 0


@pytest.mark.xdist_group(name="group7")
@pytest.mark.order(2)
def test_mafft_anno_upload_ebola(monkeypatch, api_url, tmpfile_name):
    """Test ebola sample import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)

    command_import = f"import --db {api_url} -r NC_002549.1 --method 1 --fasta ../../../test-data/ebola/ebola_20.fasta.xz --cache {tmpfile_name}/mafft -t 2 --skip-nx --must-pass-paranoid"
    code = run_cli(command_import)
    command_samples = f"import --db {api_url} -r NC_002549.1 --tsv ../../../test-data/ebola/ebola_20.tsv --cache {tmpfile_name}/mafft --cols name=name"
    code = run_cli(command_samples)
    assert code == 0


@pytest.mark.xdist_group(name="group6")
@pytest.mark.order(2)
def test_mafft_anno_upload_dengue_type2(monkeypatch, api_url, tmpfile_name):
    """Test dengue sample import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)

    command_import = f"import --db {api_url} -r NC_001474.2 --method 1 --fasta ../../../test-data/dengue/type_2/dengue_type2_complete_13.fasta.xz --cache {tmpfile_name}/mafft -t 2 --skip-nx --must-pass-paranoid"
    code = run_cli(command_import)
    command_samples = f"import --db {api_url} -r NC_001474.2  --tsv ../../../test-data/dengue/type_2/dengue_type2_complete_13.tsv --cache {tmpfile_name}/mafft --cols name=name"
    code = run_cli(command_samples)
    assert code == 0


@pytest.mark.xdist_group(name="group5")
@pytest.mark.order(2)
def test_mafft_upload_hiv(monkeypatch, api_url, tmpfile_name):
    """Test hiv sample import command using mafft method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setattr(
        "mpire.WorkerPool.map_unordered",
        lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
            func(arg) for arg in args
        ),
    )

    def smart_imap_unordered(self, func, args_list, **kwargs):
        """
        Checks if WorkerPool and function is initialized with shared_objects.

        - If WorkerPool has shared_objects → pass it as first arg (paranoid check)
        - Otherwise → don't pass it (normal alignment)
        """
        # functions that need shared_objects
        needs_shared_objects = ["process_paranoid_batch_worker"]
        func_name = getattr(func, "__name__", "")
        for data_dict in args_list:
            if func_name in needs_shared_objects:
                # Case: paranoid processing (needs shared_objects)
                # Get cache instance from the bound method
                cache_instance = getattr(func, "__self__", None)

                # Serialize cache instance to dict (mimicking mpire's shared_objects)
                if cache_instance:
                    cache_data = {
                        "basedir": cache_instance.basedir,
                        "refacc": cache_instance.refacc,
                        "refmols": cache_instance.refmols,
                        "error_dir": cache_instance.error_dir,
                        # Add other needed attributes
                    }
                else:
                    cache_data = {}
                yield func(cache_data, **data_dict)
            else:
                # Case: normal processing (no shared_objects)
                # func is a bound method (e.g., aligner.process_cached_sample)
                # so it already has 'self', just pass the dict as **kwargs
                yield func(**data_dict)

    monkeypatch.setattr("mpire.WorkerPool.imap_unordered", smart_imap_unordered)
    command_import = f"import --db {api_url} -r NC_001802.1 --method 1 --fasta ../../../test-data/HIV/HIV_20.fasta.xz --cache {tmpfile_name}/mafft -t 2 --skip-nx --must-pass-paranoid"
    code = run_cli(command_import)
    command_samples = f"import --db {api_url} -r NC_001802.1 --tsv ../../../test-data/HIV/HIV_20.tsv --cache {tmpfile_name}/mafft --cols name=name"
    code = run_cli(command_samples)
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(7)
def test_wfa_anno_no_upload_covid(monkeypatch, api_url, tmpfile_name):
    """Test import command using wfa method"""
    monkeypatch.chdir(Path(__file__).parent)
    # monkeypatch.setattr(
    #     "mpire.WorkerPool.imap_unordered",
    #     lambda self, func, args=(), kwds={}, callback=None, error_callback=None: (
    #         func(**arg) for arg in args
    #     ),
    # )
    command = f"import --db {api_url} -r MN908947.3 --method 3 --fasta ../../../test-data/sars-cov-2/SARS-CoV-2_6.fasta.gz --cache {tmpfile_name}/wfa -t 1 --no-upload --auto-anno --must-pass-paranoid --skip-nx"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group2")
@pytest.mark.order(3)
def test_wfa_anno_no_upload_mpox(monkeypatch, api_url, tmpfile_name):
    """Test import command using wfa method"""
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setenv(
        "sonar_cli.config.FILTER_DELETE_SIZE", "200000"
    )  # we keep all sequences

    command = f"import --db {api_url}  -r NC_063383.1 --method 3 --fasta ../../../test-data/mpox/mpox_20.fasta.xz --cache {tmpfile_name}/wfa -t 1 --no-upload --auto-anno --must-pass-paranoid --skip-nx"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(8)
def test_add_prop_autolink(monkeypatch, api_url, tmpfile_name):
    """Test import command using autolink"""
    monkeypatch.chdir(Path(__file__).parent)

    command = f"import --db {api_url} -r MN908947.3 --method 1 --cache {tmpfile_name}/mafft -t 1  --tsv sars-cov-2/meta_autolink.tsv --cols name=IMS_ID --auto-link"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(9)
def test_add_prop(monkeypatch, api_url, tmpfile_name):
    """Test import command using parasail method"""
    monkeypatch.chdir(Path(__file__).parent)

    command = f"import --db {api_url} -r MN908947.3 --method 1 --cache {tmpfile_name}/mafft -t 2 --tsv ../../../test-data/sars-cov-2/SARS-CoV-2_6.tsv --cols name=IMS_ID collection_date=DATE_DRAW sequencing_tech=SEQ_TYPE sample_type=SAMPLE_TYPE"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group9")
@pytest.mark.order(2)
def test_add_influenza_sequences(monkeypatch, api_url, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)
    command = f"import --db {api_url} -r NC_026438.1 --method 1 --fasta ../../../test-data/influenza/influenza-A/H1N1PDM_California/H1N1.sequences.fasta.xz --cache {tmpfile_name}/mafft_influ -t 7 --auto-anno"
    code = run_cli(command)

    assert code == 0


@pytest.mark.xdist_group(name="group9")
@pytest.mark.order(3)
def test_add_influenza_samples(monkeypatch, api_url, tmpfile_name):
    monkeypatch.chdir(Path(__file__).parent)
    command = f"import --db {api_url} -r NC_026438.1 --tsv ../../../test-data/influenza/influenza-A/H1N1PDM_California/H1N1PDM.sequences.tsv --cache {tmpfile_name}/mafft_influ --cols name=name collection_date=date country=location lineage=lineages sequences=sequences"
    code = run_cli(command)

    assert code == 0
