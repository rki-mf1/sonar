from covsonar_backend.settings import DEBUG
from rest_api.models import Sequence


def clean_unused_sequences():
    # Check the occurrences of each sequence (seqhash) in the table.
    # Delete the sequence if it is not associated with any samples.
    # Otherwise, leave it unchanged.
    seqhash_result = Sequence.objects.filter(samples__id__isnull=True)
    deleted_seqhash = seqhash_result.delete()

    if DEBUG:
        print("Deleted seqhash:", deleted_seqhash)
