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
    expected_list_count = 1

    def test_get_alignment_data(self):
        view = self.viewset.as_view({"get": "get_alignment_data"})
        request = self.factory.get("/api/alignment/")
        user = self.get_request_user()
        force_authenticate(request, user=user)
        response = view(
            request, replicon_id=1, seqhash="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["replicon_id"], 1)


class SampleViewSetTest(
    mixins.FixtureAPITestCase,
    mixins.ListViewSetTestMixin,
    mixins.CreateViewSetTestMixin,
    mixins.UpdateViewSetTestMixin,
):
    model = models.Sample
    viewset = SampleViewSet
    expected_list_count = 1

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
                },
                1,
            ),
            ("Replicon", {"label": "filter_replicon", "accession": "MN908947.3"}, 180),
            # ("Sample", "filter_sample", {}, 1),
            # ("Sublineages", "filter_sublineages", {}, 1),
        ]
    )
    def test_genome_filters(self, _, filter, expected):
        view = self.viewset.as_view({"get": "list"})

        request = self.factory.get(
            f"/api/samples/genomes/", {"filters": {"andFilter": [filter]}}
        )
        user = self.get_request_user()
        force_authenticate(request, user=user)
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), expected)
