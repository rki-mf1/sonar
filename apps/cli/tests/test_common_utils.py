from sonar_cli.common_utils import flatten_json_output


SAMPLE = {
    "name": "S1",
    "properties": [{"name": "lineage", "value": "BA.1"}],
    "genomic_profiles": {
        "MN908947.3": {
            "C241T": ["stop_gained HIGH"],
            "A405G": [],
        }
    },
    "proteomic_profiles": {
        "MN908947.3: cds-ORF1ab": {
            "ORF1ab:S123L": ["stop_gained HIGH", "missense_variant MODERATE"],
            "S:D614G": [],
        }
    },
}


def test_flatten_includes_annotations_by_default():
    row = flatten_json_output([SAMPLE])[0]
    # genomic: annotation appended in parentheses, bare label when no annotation
    assert row["genomic_profiles"] == "MN908947.3(C241T(stop_gained HIGH), A405G)"
    # proteomic: same shape, multiple annotations joined with "; "
    assert row["proteomic_profiles"] == (
        "MN908947.3: cds-ORF1ab("
        "ORF1ab:S123L(stop_gained HIGH; missense_variant MODERATE), S:D614G)"
    )


def test_flatten_excludes_annotations_with_flag():
    row = flatten_json_output([SAMPLE], exclude_annotation=True)[0]
    assert row["genomic_profiles"] == "MN908947.3(C241T, A405G)"
    assert row["proteomic_profiles"] == "MN908947.3: cds-ORF1ab(ORF1ab:S123L, S:D614G)"


def test_flatten_handles_missing_profiles():
    row = flatten_json_output([{"name": "E"}])[0]
    assert row["genomic_profiles"] == ""
    assert row["proteomic_profiles"] == ""
