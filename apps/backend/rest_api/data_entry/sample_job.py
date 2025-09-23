from covsonar_backend.settings import DEBUG
from covsonar_backend.settings import LOGGER
from rest_api.data_entry.sequence_job import clean_unused_sequences
from rest_api.models import Alignment
from rest_api.models import Sample
from rest_api.models import Sample2Property
from rest_api.models import Sequence


def delete_sample(sample_list: list):
    data = {}
    # TODO delete sequence or sample + all related sequences
    filtered_ref_sequence = Sequence.objects.filter(name__in=sample_list)
    sample_ids = list(filtered_ref_sequence.values_list("id", flat=True))
    seqhash_ids = list(filtered_ref_sequence.values_list("sequence_id", flat=True))
    deleted_sample = filtered_ref_sequence.delete()
    LOGGER.info(f"Sample IDs: {sample_ids}")
    if DEBUG:
        print("\n")
        print("Seqhash IDs", seqhash_ids)
        # number of objects deleted and a dictionary with the number of deletions per object type
    LOGGER.info(f"Deleted sample: {deleted_sample}")

    # Filter sequences without associated samples
    clean_unused_sequences()

    # TODO: Delete Annotation

    data["deleted_samples_count"] = (
        deleted_sample[1]["rest_api.Sample"] if deleted_sample[0] != 0 else 0
    )

    return data


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
