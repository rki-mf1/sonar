from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from sonar_backend.version import get_version


@api_view(["GET"])
@permission_classes([AllowAny])
def status(request):
    return Response({"name": "sonar-backend", "version": get_version()})
