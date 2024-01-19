import pathlib
from rest_framework.response import Response
from rest_framework import status
from django.core.files.uploadedfile import InMemoryUploadedFile


def create_error_response(
    message="", detail=None, return_status=status.HTTP_400_BAD_REQUEST
):
    json_response = {"status": "error"}
    if message:
        json_response["message"] = message
    if detail:
        json_response["detail"] = message
    return Response(
        json_response, status=return_status, content_type="application/json"
    )


def create_success_response(message="", data=None, return_status=status.HTTP_200_OK):
    json_response = {"status": "success", "data": data}
    if message:
        json_response["message"] = message
    return Response(
        json_response, status=return_status, content_type="application/json"
    )


def write_to_file(_path: pathlib.Path, file_obj: InMemoryUploadedFile):
    _path.parent.mkdir(exist_ok=True, parents=True)
    with open(_path, "wb") as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
