import pathlib
from rest_framework.response import Response
from rest_framework import status
from django.core.files.uploadedfile import InMemoryUploadedFile

IUPAC_CODES = {
    "nt": {
        "A": set("A"),
        "C": set("C"),
        "G": set("G"),
        "T": set("T"),
        "R": set("AGR"),
        "Y": set("CTY"),
        "S": set("GCS"),
        "W": set("ATW"),
        "K": set("GTK"),
        "M": set("ACM"),
        "B": set("CGTB"),
        "D": set("AGTD"),
        "H": set("ACTH"),
        "V": set("ACGV"),
        "N": set("ACGTRYSWKMBDHVN"),
        "n": set("N"),
    },
    "aa": {
        "A": set("A"),
        "R": set("R"),
        "N": set("N"),
        "D": set("D"),
        "C": set("C"),
        "Q": set("Q"),
        "E": set("E"),
        "G": set("G"),
        "H": set("H"),
        "I": set("I"),
        "L": set("L"),
        "K": set("K"),
        "M": set("M"),
        "F": set("F"),
        "P": set("P"),
        "S": set("S"),
        "T": set("T"),
        "W": set("W"),
        "Y": set("Y"),
        "V": set("V"),
        "U": set("U"),
        "O": set("O"),
        "B": set("DNB"),
        "Z": set("EQZ"),
        "J": set("ILJ"),
        "Φ": set("VILFWYMΦ"),
        "Ω": set("FWYHΩ"),
        "Ψ": set("VILMΨ"),
        "π": set("PGASπ"),
        "ζ": set("STHNQEDKRζ"),
        "+": set("KRH+"),
        "-": set("DE-"),
        "X": set("ARNDCQEGHILKMFPSTWYVUOBZJΦΩΨπζ+-X"),
        "x": set("X"),
    },
}

def create_error_response(message='', detail=None, return_status=status.HTTP_400_BAD_REQUEST):
    json_response = {'status': 'error'}
    if message:
        json_response['message'] = message
    if detail:
        json_response['detail'] = message
    return Response(
        json_response,
        status=return_status, content_type='application/json'
    )

def create_success_response(message='', data=None, return_status=status.HTTP_200_OK):
    json_response = {'status': 'success', 'data': data}
    if message:
        json_response['message'] = message
    return Response(
        json_response,
        status=return_status,
        content_type='application/json'
    )

def write_to_file(_path: pathlib.Path, file_obj: InMemoryUploadedFile):
    _path.parent.mkdir(exist_ok=True, parents=True)
    with open(_path, 'wb') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)        


# distutils will no longer be part of the standard library, 
# here is the code for distutils.util.strtobool() (see the source code for 3.11.2).
def strtobool (val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))
    
def resolve_ambiguous_NT_AA(type, char):
    try:
        selected_chars= list(IUPAC_CODES[type][char])
    except KeyError:
        raise KeyError(f"Invalid notation '{char}'.")
    
    return selected_chars