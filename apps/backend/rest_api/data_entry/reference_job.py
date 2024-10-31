from rest_api.models import Alignment, Reference


def delete_reference(reference_accession):
    data = {"samples_count": 0}
    # sample that link to this reference_accession
    data["samples_count"] = Alignment.objects.filter(
        replicon__reference__accession=reference_accession
    ).count()
    _ref = Reference.objects.filter(accession=reference_accession)
    _ref.delete()

    # check if sample likned to any ref? if none also delete it
    # and property as well....

    return data
