import json

from parameterized import parameterized
from rest_framework import status
from rest_framework.test import force_authenticate

from rest_api import models
from rest_api import viewsets
from rest_api.test import mixins
from rest_api.viewsets_sample import SampleViewSet


class AlignmentViewSetTest(
    mixins.FixtureAPITestCase,
    mixins.ListViewSetTestMixin,
    mixins.CreateViewSetTestMixin,
    mixins.UpdateViewSetTestMixin,
):
    model = models.Alignment
    viewset = viewsets.AlignmentViewSet
    expected_list_count = 10

    def test_get_alignment_data(self):
        pass  # TODO


class SampleViewSetTest(
    mixins.FixtureAPITestCase,
    mixins.ListViewSetTestMixin,
    mixins.CreateViewSetTestMixin,
    mixins.UpdateViewSetTestMixin,
):
    model = models.Sample
    viewset = SampleViewSet
    expected_list_count = 10

    @parameterized.expand(
        [
            (
                "Property",
                {
                    "label": "Property",
                    "property_name": "zip_code",
                    "filter_type": "exact",
                    "value": "40477",
                    "exclude": False,
                },
                3,
            ),
            (
                "SNP Nt",
                {
                    "label": "SNP Nt",
                    "ref_nuc": "T",
                    "ref_pos": 670,
                    "alt_nuc": "G",
                    "exclude": False,
                },
                10,
            ),
            (
                "Del AA",
                {
                    "label": "Del AA",
                    "protein_symbol": "ORF1a",
                    "first_deleted": 2084,
                    "last_deleted": 2086,
                    "exclude": False,
                },
                0,
            ),
            (
                "Del AA",
                {
                    "label": "Del AA",
                    "protein_symbol": "ORF1a",
                    "first_deleted": 3675,
                    "last_deleted": 3676,
                    "exclude": False,
                },
                10,
            ),
            (
                "Del Nt",
                {
                    "label": "Del Nt",
                    "first_deleted": 11287,
                    "last_deleted": 1129,
                    "exclude": False,
                },
                0,
            ),
            (
                "Del Nt",
                {
                    "label": "Del Nt",
                    "first_deleted": 29734,
                    "last_deleted": 29759,
                    "exclude": False,
                },
                10,
            ),
            (
                "Ins AA",
                {
                    "label": "Ins AA",
                    "protein_symbol": "S",
                    "ref_aa": "R",
                    "ref_pos": 21608,
                    "alt_aa": "RGTCATGCCGCTGTEPE",
                },
                0,
            ),
            (
                "Ins Nt",
                {
                    "label": "Ins Nt",
                    "ref_nuc": "G",
                    "ref_pos": 21608,
                    "alt_nuc": "GTCATGCCGCTGT",
                },
                10,
            ),
            ("Replicon", {"label": "Replicon", "accession": "MN908947.3"}, 10),
        ]
    )
    def test_genome_filters(self, _, filter, expected_count):
        view = self.viewset.as_view({"get": "genomes"})
        request = self.factory.get(
            "/api/samples/genomes/", {"filters": json.dumps({"andFilter": [filter]})}
        )
        user = self.get_request_user()
        force_authenticate(request, user=user)
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], expected_count)
