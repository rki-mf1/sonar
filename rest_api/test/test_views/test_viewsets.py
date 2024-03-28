import json
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
    expected_list_count = 180

    def test_get_alignment_data(self):
        pass #TODO


class SampleViewSetTest(
    mixins.FixtureAPITestCase,
    mixins.ListViewSetTestMixin,
    mixins.CreateViewSetTestMixin,
    mixins.UpdateViewSetTestMixin,
):
    model = models.Sample
    viewset = SampleViewSet
    expected_list_count = 180

    @parameterized.expand(
        [
            (
                "Property",
                {
                    "label": "Property",
                    "property_name": "sample_type",
                    "filter_type": "exact",
                    "value": "X",
                    "exclude": False,
                },
                48,
            ),
            (
                "SNP Nt",
                {
                    "label": "SNP Nt",
                    "ref_nuc": "A",
                    "ref_pos": 1,
                    "alt_nuc": 1,
                    "exclude": False,
                },
                1,
            ),
            (
                "SNP AA",
                {
                    "label": "SNP AA",
                    "protein_symbol": "orf1ab",
                    "ref_aa": "T",
                    "ref_pos": 403,
                    "alt_aa": "P",
                    "exclude": False,
                },
                26,
            ),
            (
                "Del Nt",
                {
                    "label": "Del Nt",
                    "first_deleted": 69,
                    "last_deleted": 69,
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
                81,
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
                26,
            ),
            (
                "Ins AA",
                {
                    "label": "Ins AA",
                    "protein_symbol": "orf1ab",
                    "ref_nuc": "T",
                    "ref_pos": 2196,
                    "alt_nuc": "E",
                },
                1,
            ),
            ("Replicon", {"label": "filter_replicon", "accession": "MN908947.3"}, 180),
            # ("Sample", "filter_sample", {}, 1),
            # ("Sublineages", "filter_sublineages", {}, 1),
        ]
    )
    def test_genome_filters(self, _, filter, expected):
        print(_)
        view = self.viewset.as_view({'get': 'genomes'})        
        request = self.factory.get(
            "/api/samples/genomes/", {"filters": json.dumps({"andFilter": [filter]})}
        )
        user = self.get_request_user()
        force_authenticate(request, user=user)
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], expected)
