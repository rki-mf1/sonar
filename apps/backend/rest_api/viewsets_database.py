from rest_api.utils import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action

from .viewsets_sample import SampleViewSet


class DatabaseInfoView(
    viewsets.GenericViewSet,
):
    @action(detail=False, methods=["get"])  # detail=False means it's a list action
    def get_database_info(self, request, *args, **kwargs):
        dict = {}
        queryset = SampleViewSet()._get_filtered_queryset(request)

        dict["meta_data_coverage"] = SampleViewSet()._get_meta_data_coverage(queryset)

        return Response(data={"detail": dict}, status=status.HTTP_200_OK)
