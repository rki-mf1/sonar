import pytest

from .conftest import run_cli
from .conftest import run_cli_cmd


def test_match(api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3")
    assert code == 0


def test_match_pipe(capfd, api_url):
    result = run_cli_cmd(f"sonar-cli match --db {api_url} -r MN908947.3 ")
    assert result.returncode == 0, f"Expected exit code 0 but got {result}"

    # Check if the output contains the word "name"
    result = run_cli_cmd(
        f"sonar-cli match --db {api_url} -r MN908947.3 --out-cols name | head -n 10"
    )
    captured = capfd.readouterr()
    assert "name" in captured.out
    assert result.returncode == 0, f"Expected exit code 0 but got {result}"
    # check for stderr to ensure there were not in output
    assert "BrokenPipeError" not in captured.out


# match covid
@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(15)
def test_match_profile_count_covid(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3  --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "18" == lines[-1]
    assert code == 0


def test_match_profile_covid(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --profile G22992A --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "9" == lines[-1]
    assert code == 0


def test_match_profile_AND(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3  --profile T24469A C26858T --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "3" == lines[-1]
    assert code == 0


def test_match_profile_OR(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --profile A1741G --profile G22992A --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "10" == lines[-1]
    assert code == 0


def test_match_profile_AA(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --profile S:T19R --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "2" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(16)
def test_match_profile_OR_AA(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --profile N:P13L --profile S:N501Y  --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "15" == lines[-1]
    assert code == 0


def test_match_profile_showNX(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --profile S:T19R --showNX")
    out, err = capfd.readouterr()
    assert "A28213N" in out
    assert "ORF8:L118X" in out
    assert code == 0


def test_match_profile_exactN(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --profile A27624n --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "2" == lines[-1]
    assert code == 0


def test_match_profile_exactX(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --profile ORF7a:Q76x --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "2" == lines[-1]
    assert code == 0


def test_match_profile_NT_INS(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --profile A29903NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
    assert code == 0


def test_match_varchar_NULL(capfd, api_url):
    code = run_cli(f'match --db {api_url} -r MN908947.3 --lab "" --count')
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
    assert code == 0


def test_match_varchar_widecard(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --lab %101% --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "5" == lines[-1]
    assert code == 0


def test_match_prop_text(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --comments %mysteries% --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "2" == lines[-1]
    assert code == 0


def test_match_prop_text_NULL(capfd, api_url):
    code = run_cli(f'match --db {api_url} -r MN908947.3 --comments "" --count')
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "0" == lines[-1]
    assert code == 0


def test_match_prop_int(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --age 16 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(17)
def test_match_prop_int_not(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --age ^16 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "17" == lines[-1]
    assert code == 0


def test_match_prop_int_range(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --age 50:80 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "3" == lines[-1]
    assert code == 0


def test_match_prop_int_gt(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --age '>80' --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "6" == lines[-1]
    assert code == 0


def test_match_prop_int_lt(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --age '<70' --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "5" == lines[-1]
    assert code == 0


def test_match_prop_float(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --euro 66.11 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
    assert code == 0


def test_match_prop_float_not(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --euro '^66.11' --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "17" == lines[-1]
    assert code == 0


def test_match_prop_float_range(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --euro '30:66.11' --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "6" == lines[-1]
    assert code == 0


def test_match_prop_float_gt(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --euro 31.16 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
    assert code == 0


def test_match_prop_float_lt(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --euro '<42.64' --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "6" == lines[-1]
    assert code == 0


def test_match_prop_date(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --collection_date 2022-01-30  --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
    assert code == 0


def test_match_prop_date_range(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --collection_date 2022-01-30:2022-06-30  --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "6" == lines[-1]
    assert code == 0


def test_match_prop_zip(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --zip_code 16816  --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(18)
def test_match_prop_zip_not(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --zip_code ^16816  --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "17" == lines[-1]
    assert code == 0


def test_match_prop_complex_1(capfd, api_url):
    # combine AA and AA AND PROP
    code = run_cli(
        f"match --db {api_url}  -r MN908947.3 --profile S:E484A S:N501Y --collection_date 2022-01-30 --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
    assert code == 0

    code = run_cli(
        f"match --db {api_url}  -r MN908947.3 --profile S:E484K S:N501Y --collection_date 2022-01-30 --count "
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "0" == lines[-1]
    assert code == 0


def test_match_prop_complex_2(capfd, api_url):
    # seach on given samples and get only samples that contain sequencing reason is N
    code = run_cli(
        f"match --db {api_url} "
        "-r MN908947.3 "
        "--sample IMS-10150-CVDP-469B04EB-4D49-4109-9F81-0531CE275F6D "
        "IMS-10768-CVDP-0E69A26F-7AC0-4631-B0F3-192FF005FDA0 "
        "IMS-10013-CVDP-7629957A-D507-442D-BD2A-18236F7DB38C "
        "--sequencing_reason N "
        "--count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "2" == lines[-1]
    assert code == 0


def skip_test_match_prop_complex_3():
    # combine AA OR NT OR AA AND PROP
    pass


def test_match_prop_complex_4(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --lineage BA.1 --profile C25584T --with-sublineage --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "4" == lines[-1]
    assert code == 0


def test_match_profile_NT_DEL(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --profile del:21987-21995 --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "3" == lines[-1]
    assert code == 0


def test_match_profile_AA_INS(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --profile S:R214REPE --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "2" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(19)
def test_match_profile_AA_DEL(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --profile ORF1a:del:3675-3677 --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "10" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(20)
def test_match_profile_NT_DEL_single(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --profile del:28271 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "5" == lines[-1]
    assert code == 0


def test_match_profile_AA_DEL_single(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --profile S:del:157 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "2" == lines[-1]
    assert code == 0


def test_match_prop_varchar_lineage(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --lineage BA.1.1 AY.4 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "3" == lines[-1]
    assert code == 0


def test_match_prop_varchar_sublineage(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --lineage BA.1 --with-sublineage --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "6" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(21)
def test_match_prop_varchar_not(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --sequencing_reason ^X --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "12" == lines[-1]
    assert code == 0


def test_match_prop_varchar(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --sequencing_reason X  --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "5" == lines[-1]
    assert code == 0


def test_match_anno_type(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --anno-type disruptive_inframe_insertion --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "2" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(22)
def test_match_anno_impact(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --anno-impact HIGH --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    # assert "1" == lines[-1]
    assert "5" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(23)
def test_match_anno_impact_and_profile(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --anno-impact MODERATE --profile C24503T --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "4" == lines[-1]
    assert code == 0


def test_match_anno_impact_and_prop(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --anno-impact MODERATE  --age '>50' --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "9" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(24)
def test_match_anno_impact_and_type(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --anno-impact HIGH --anno-type stop_gained --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    # assert "1" == lines[-1]
    assert "5" == lines[-1]
    assert code == 0


# match rsv
@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(15)
def test_match_profile_count_rsv(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r OP975389.1  --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "20" == lines[-1]
    assert code == 0


def test_match_aa_mut_rsv(capfd, api_url):
    code = run_cli(f"match --db {api_url}  -r OP975389.1 --profile SH:K53E --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
    assert code == 0


# match mpox
@pytest.mark.xdist_group(name="group4")
@pytest.mark.order(3)
def test_match_profile_count_mpox(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r NC_063383.1  --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "2" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group4")
@pytest.mark.order(4)
def test_match_aa_mut_mpox(capfd, api_url):
    code = run_cli(
        f"match --db {api_url}  -r NC_063383.1 --profile OPG136:D98L --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "2" == lines[-1]
    assert code == 0


# match ebola
@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(15)
def test_match_profile_count_ebola(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r NC_002549.1  --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "20" == lines[-1]
    assert code == 0


def test_match_aa_mut_ebola(capfd, api_url):
    code = run_cli(
        f"match --db {api_url}  -r NC_002549.1 --profile L:V1597A GP:K478R --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "5" == lines[-1]
    assert code == 0


# match dengue
@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(15)
def test_match_profile_count_dengue(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r NC_001474.2 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "13" == lines[-1]
    assert code == 0


# TODO adapt to mat_peptide
def test_match_aa_mut_dengue(capfd, api_url):
    code = run_cli(f"match --db {api_url}  -r NC_001474.2 --profile POLY:N997S --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "13" == lines[-1]
    assert code == 0


# match hiv
@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(15)
def test_match_profile_count_hiv(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r NC_001802.1 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "20" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(16)
def test_match_aa_mut_hiv(capfd, api_url):
    code = run_cli(
        f"match --db {api_url}  -r NC_001802.1 --profile env:Q344R nef:R29E --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "4" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(17)
def test_match_multiple_genes_in_same_region_hiv(capfd, api_url):
    # test mutations within 2 genes in same region: gene gag-pol (336..1637,1637..4642), gene gag: 336..1838,
    code = run_cli(
        f"match --db {api_url}  -r NC_001802.1 --profile gag-pol:K424I gag:K424I --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
    assert code == 0
    # multiple genes in same region: gene gag-pol (336..1637,1637..4642), gene gag: 336..1838 different translation part
    code = run_cli(
        f"match --db {api_url}  -r NC_001802.1 --profile gag-pol:L441P gag:Y441R --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "3" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group3")
@pytest.mark.order(3)
def test_match_aa_influ(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r NC_026438.1 --profile HA:S220T --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()

    assert "16" == lines[-1]
    assert code == 0


def test_match_aa_2_influ(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r NC_026438.1 --profile CY121680.1:HA:S220T --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()

    assert "16" == lines[-1]
    assert code == 0


def test_match_nt_snp_influ(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r NC_026438.1 --profile NC_026435.1:C447G --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()

    assert "1" == lines[-1]
    assert code == 0


def test_fail_match_nt_snp_influ(capfd, api_url):
    with pytest.raises(SystemExit) as e:
        run_cli(f"match --db {api_url} -r NC_026438.1 --profile C447G --count")
    out, err = capfd.readouterr()
    assert "Reference NC_026438.1 has 8 replicons" in err
    assert e.value.code == 1


def test_match_nt_ins_influ(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r NC_026438.1 --profile NC_026435.1:A2274ATGAATTTAACTTGTCCTTCATGAAAAAATGCTTGTTTCTACTA --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()

    assert "1" == lines[-1]
    assert code == 0


def test_match_nt_del_influ(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r NC_026438.1 --profile CY121680.1:del:1722-1752 --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()

    assert "16" == lines[-1]
    assert code == 0
