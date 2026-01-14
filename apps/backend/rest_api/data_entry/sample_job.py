from covsonar_backend.settings import DEBUG
from covsonar_backend.settings import LOGGER
from rest_api.data_entry.sequence_job import clean_unused_sequences
from rest_api.models import Alignment
from rest_api.models import Sample
from rest_api.models import Sample2Property
from rest_api.models import Sequence


def delete_sequences(sequence_list: list):
    """
    Delete sequences by name and cascade-delete all related samples,
    alignments, properties, annotations, etc.
    """
    data = {}
    sequences_qs = Sequence.objects.filter(name__in=sequence_list)

    if not sequences_qs.exists():
        LOGGER.warning(f"No sequences found for deletion: {sequence_list}")
        return {"deleted_sequences_count": 0}

    deleted_info = (
        sequences_qs.delete()
    )  # cascade deletion, returns (num_deleted, dict_of_models)
    LOGGER.info(f"Deleted sequence: {deleted_info}")

    # Filter sequences without associated samples
    clean_unused_sequences()

    data["deleted_sequences_count"] = deleted_info[1].get("rest_api.Sequence", 0)
    return data


def delete_samples(sample_list: list):
    """
    delte samples and all related sequences, alignments, properties
    """
    data = {}
    samples_qs = Sample.objects.filter(name__in=sample_list)

    if not samples_qs.exists():
        LOGGER.warning(f"No samples found for deletion: {sample_list}")
        return {"deleted_samples_count": 0}

    sample_ids = list(samples_qs.values_list("id", flat=True))
    sequence_ids = list(samples_qs.values_list("sequence_id", flat=True))
    LOGGER.info(f"Deleting samples with IDs: {sample_ids}")
    if DEBUG:
        print("\nAssociated sequence IDs", sequence_ids)

    deleted_info = samples_qs.delete()  # returns (num_deleted, dict_of_models)
    LOGGER.info(f"Deleted samples: {deleted_info}")

    # Filter sequences without associated samples
    clean_unused_sequences()

    data["deleted_samples_count"] = deleted_info[1].get("rest_api.Sample", 0)
