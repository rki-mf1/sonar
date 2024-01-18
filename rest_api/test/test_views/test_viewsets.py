from parameterized import parameterized
from rest_framework import status
from rest_framework.test import force_authenticate

from rest_api.test import mixins
from rest_api import models, viewsets


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
        response = view(request, replicon_id=1, seqhash="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
