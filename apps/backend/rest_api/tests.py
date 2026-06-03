import os
from unittest.mock import patch

from rest_framework import status as drf_status
from rest_framework.test import APITestCase


class StatusViewTests(APITestCase):
    def test_status_returns_backend_version(self):
        with patch.dict(os.environ, {"SONAR_VERSION": "9.9.9"}):
            response = self.client.get("/api/status/")

        self.assertEqual(response.status_code, drf_status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"name": "sonar-backend", "version": "9.9.9"},
        )
