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


# deprecated, just for reference.
def delete_sample_old(reference_accession, sample_list: list):
    """
    NOTE: This function allows for the deletion of a specific
    alignment by passing its reference ID as a parameter.
    """
    data = {
        "NOTE": "These are the numbers that need to be deleted.",
        "samples_count": 0,
        "properties_count": 0,
        "alignments_count": 0,
        "seqhashes_count": 0,
    }
    # filter by reference_accession, sample_list
    # sample that link to this reference_accession
    filtered_ref_sample = Sample.objects.filter(
        sequence__alignments__replicon__reference__accession=reference_accession,
        name__in=sample_list,
    )
    if DEBUG:
        print("------------")
        print("Query Sample:", filtered_ref_sample.query)
        print("\n")
        print("Query result:", filtered_ref_sample)

    sample_ids = list(filtered_ref_sample.values_list("id", flat=True))
    seqhash_ids = list(filtered_ref_sample.values_list("sequence_id", flat=True))
    sample_count = filtered_ref_sample.count()
    if DEBUG:
        print("\n")
        print("Sample IDs", sample_ids)
        print("Seqhash IDs", seqhash_ids)

    if not sample_ids:
        return data

    # delete sample alignment
    aligns = Alignment.objects.filter(sequence__sample__id__in=sample_ids)
    if DEBUG:
        print("------------")
        print("Query Alignment:", aligns.query)
        print("\n")
        print("Query result:", aligns)

    align_count = aligns.count()
    aligns.delete()
    # delete Alignment2Mutation --> CASCADE
    # delete Mutation --> do nothing, we leave it
    # delete mutation2annotation  --> do nothing , we leave it

    # delete sample2property
    # delete it by using code below or change the setting to CASCADE
    sam2prop = Sample2Property.objects.filter(sample_id__in=sample_ids)
    if DEBUG:
        print("------------")
        print("Query Sample2Property:", sam2prop.query)
        print("\n")
        print("Query result:", sam2prop)

    sam2prop_count = sam2prop.count()
    sam2prop.delete()

    # -------- NOTE : NOT working
    filtered_ref_sample = Sample.objects.filter(
        sequence__alignments__replicon__reference__accession=reference_accession,
        name__in=sample_list,
    )
    filtered_ref_sample.delete()
    if DEBUG:
        print("------------")
        print("Query Sample:", filtered_ref_sample.query)
        print("\n")
        print("Query result:", filtered_ref_sample)
    # filtered_ref_sample.delete()  # <--- Why?\ it seems the delete function sample does not work or get called

    # delete seqhash
    # Check the sequence (seqhash) to see how many occurrences are left in the table.
    # If we delete the last sample that use this seqhash, in this case, we also delete seqhash too;
    # otherwise, we leave it as it is.
    """
    SELECT sequence.id, sequence.seqhash,
    FROM sequence
    LEFT JOIN sample ON sequence.id = sample.id
    WHERE sample.id IS NULL;
    """
    seqhash_result = Sequence.objects.filter(samples__id__isnull=True)
    if DEBUG:
        print("------------")
        print("Query seqhash_result:", seqhash_result.query)
        print("\n")
        print("Query result:", seqhash_result)

    seqhash_count = seqhash_result.count()
    seqhash_result.delete()

    data["samples_count"] = sample_count
    data["properties_count"] = sam2prop_count
    data["alignments_count"] = align_count
    data["seqhashes_count"] = seqhash_count

    return data
