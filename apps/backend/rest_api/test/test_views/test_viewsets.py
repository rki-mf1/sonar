import json
from django.test import TransactionTestCase
from parameterized import parameterized
from rest_framework import status
from rest_framework.test import force_authenticate

from rest_api.test import mixins
from rest_api import models, viewsets
from rest_api.viewsets_sample import SampleViewSet


class AlignmentViewSetTest(
    mixins.FixtureAPITestCase,
    mixins.ListViewSetTestMixin,
    mixins.CreateViewSetTestMixin,
    mixins.UpdateViewSetTestMixin,
):
    model = models.Alignment
    viewset = viewsets.AlignmentViewSet
    expected_list_count = 15

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
    expected_list_count = 15

    @parameterized.expand(
        [
            (
                "Property",
                {
                    "label": "Property",
                    "property_name": "zip_code",
                    "filter_type": "exact",
                    "value": "51375.0",
                    "exclude": False,
                },
                2,
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
                6,
            ),
            (
                "SNP AA",
                {
                    "label": "SNP AA",
                    "protein_symbol": "S",
                    "ref_aa": "T",
                    "ref_pos": 716,
                    "alt_aa": "I",
                    "exclude": False,
                },
                3,
            ),
            (
                "Del Nt",
                {
                    "label": "Del Nt",
                    "first_deleted": 1,
                    "last_deleted": 245,
                    "exclude": False,
                },
                1,
            ),
            (
                "Del AA",
                {
                    "label": "Del AA",
                    "protein_symbol": "S",
                    "first_deleted": 69,
                    "last_deleted": 69,
                    "exclude": False,
                },
                6,
            ),
            (
                "Ins Nt",
                {
                    "label": "Ins Nt",
                    "ref_nuc": "T",
                    "ref_pos": 16176,
                    "alt_nuc": "C",
                    "exclude": False,
                },
                1,
            ),
            (
                "Ins AA",
                {
                    "label": "Ins AA",
                    "protein_symbol": "S",
                    "ref_aa": "R",
                    "ref_pos": 214,
                    "alt_aa": "REPE",
                },
                3,
            ),
            ("Replicon", {"label": "Replicon", "accession": "MN908947.3"}, 15),
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
