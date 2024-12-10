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


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(9)
def test_match_profile_count(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3  --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "17" == lines[-1]
    assert code == 0


def test_match_profile(capfd, api_url):
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
@pytest.mark.order(10)
def test_match_profile_OR_AA(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --profile S:E484K --profile  S:N501Y  --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "10" == lines[-1]
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
@pytest.mark.order(11)
def test_match_prop_int_not(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --age ^16 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "16" == lines[-1]
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
    assert "16" == lines[-1]
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
@pytest.mark.order(12)
def test_match_prop_zip_not(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --zip_code ^16816  --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "16" == lines[-1]
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
@pytest.mark.order(13)
def test_match_profile_AA_DEL(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --profile ORF1ab:del:3675-3676 --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "10" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(14)
def test_match_profile_NT_DEL_single(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --profile del:28271 --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "4" == lines[-1]
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
@pytest.mark.order(15)
def test_match_prop_varchar_not(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --sequencing_reason ^X --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "11" == lines[-1]
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
@pytest.mark.order(16)
def test_match_anno_impact(capfd, api_url):
    code = run_cli(f"match --db {api_url} -r MN908947.3 --anno-impact HIGH --count")
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "6" == lines[-1]
    assert code == 0


@pytest.mark.xdist_group(name="group1")
@pytest.mark.order(17)
def test_match_anno_impact_and_profile(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --anno-impact HIGH  --profile C24503T --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "1" == lines[-1]
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
@pytest.mark.order(18)
def test_match_anno_impact_and_type(capfd, api_url):
    code = run_cli(
        f"match --db {api_url} -r MN908947.3 --anno-impact HIGH --anno-type stop_gained --count"
    )
    out, err = capfd.readouterr()
    lines = out.splitlines()
    assert "5" == lines[-1]
    assert code == 0
