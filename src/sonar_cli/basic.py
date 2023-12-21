import json
import os
from typing import Optional

from sonar_cli.dbm import sonarDBManager
from sonar_cli.utils import _write_vcf_header
from sonar_cli.utils import _write_vcf_records
from sonar_cli.utils import sonarUtils
from sonar_cli.utils_1 import get_filename_sonarhash
from sonar_cli.utils_1 import out_autodetect


class sonarBasics:
    # vcf
    def export_vcf(
        cursor,
        reference: str,
        outfile: Optional[str] = None,
        na: str = "*** no match ***",
        generate_hash_file_flag: bool = True,
        db: Optional[str] = None,
    ):  # noqa: C901
        """
        Exports data from a database result to a VCF file.

        Parameters:
        cursor: The rows object which already has been fetched data.
        reference: The reference genome name.
        outfile: The output file name. If None, output is printed to stdout.
        na: The string to print if there are no records.
        """

        if not cursor:
            print(na)
        else:
            records, all_samples = sonarUtils._get_vcf_data(cursor)
            if outfile is not None:
                # The below code is used in import process.
                # Extract the directory path from the outfile
                directory_path = os.path.dirname(outfile)
                if directory_path and not os.path.exists(directory_path):
                    os.makedirs(directory_path, exist_ok=True)

                sample_hash_list = {}
                IDs_list = {}
                # Create Sample seqhash and variant
                for row in cursor:  # sonarBasics.iter_formatted_match(cursor):
                    # print(row)
                    element_id, variant_id, samples = (
                        row["element.id"],
                        row["variant.id"],
                        row["samples"],
                    )
                    samples = samples.split(",")
                    # find samples and seqhash
                    with sonarDBManager(db, readonly=True) as dbm:

                        for sample in samples:
                            seqhash = dbm.get_seq_hash(sample)
                            # handle the hash and sample.
                            sample_hash_list[sample] = seqhash["seqhash"]
                            # handle the variant and sample.
                            if sample not in IDs_list:
                                IDs_list[sample] = []
                            IDs_list[sample].append(
                                {"element_id": element_id, "variant_id": variant_id}
                            )
                # Combine sonar_hash and reference into a single dictionary
                data = {
                    "sample_variantTable": IDs_list,
                    "sample_hashes": sample_hash_list,
                    "reference": reference,
                }

                # Remove the existing extension from outfile and then append a new extension.
                filename_sonarhash = get_filename_sonarhash(outfile)
                with open(filename_sonarhash, "w") as file:
                    json.dump(data, file)

            with out_autodetect(outfile) as handle:
                _write_vcf_header(handle, reference, all_samples)
                _write_vcf_records(handle, records, all_samples)
