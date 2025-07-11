import json
import os
from typing import Any
from typing import Dict
from typing import List

from mpire import WorkerPool
import pandas as pd
from sonar_cli.logging import LoggingConfigurator

LOGGER = LoggingConfigurator.get_logger()


def read_nextclade_json_streaming(json_file: str, chunk_size: int = 100):  # noqa: C901
    """
    Generator that reads Nextclade JSON output file in chunks to avoid memory issues
    Yields chunks of sample data instead of loading everything into memory
    """

    def process_json_data(data):
        """Extract results from JSON data structure"""
        if isinstance(data, dict):
            return data.get("results", [data] if data else [])
        elif isinstance(data, list):
            return data
        else:
            return []

    try:
        # Method 1: Try regular JSON first
        with open(json_file, "r") as f:
            # Check if it's a regular JSON by reading first few characters
            first_char = f.read(1)
            f.seek(0)

            if first_char == "{":
                # Regular JSON file
                data = json.load(f)
                results = process_json_data(data)

                # Yield in chunks
                for i in range(0, len(results), chunk_size):
                    yield results[i : i + chunk_size]
            else:
                # Likely NDJSON, process line by line
                f.seek(0)
                chunk = []
                for line in f:
                    if line.strip():
                        try:
                            sample_data = json.loads(line)
                            chunk.append(sample_data)

                            if len(chunk) >= chunk_size:
                                yield chunk
                                chunk = []
                        except json.JSONDecodeError:
                            continue

                # Yield remaining data
                if chunk:
                    yield chunk

    except json.JSONDecodeError:
        # Fallback: Try NDJSON line by line
        try:
            with open(json_file, "r") as f:
                chunk = []
                for line in f:
                    if line.strip():
                        try:
                            sample_data = json.loads(line)
                            chunk.append(sample_data)

                            if len(chunk) >= chunk_size:
                                yield chunk
                                chunk = []
                        except json.JSONDecodeError:
                            continue

                if chunk:
                    yield chunk

        except Exception as e:
            print(f"Error reading JSON file {json_file}: {str(e)}")
            return


def read_nextclade_json(json_file: str) -> Dict:
    """Read Nextclade JSON output file"""
    # Method 1: Using json.load() for regular JSON files
    try:
        with open(json_file) as f:
            data = json.load(f)
            return data.get("results", data) if data else None
    except json.JSONDecodeError:
        # Method 2: Fallback for NDJSON - read line by line
        try:
            with open(json_file) as f:
                data = []
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
                return data if data else None
        except Exception as e:
            print(f"Error reading JSON file: {str(e)}")
            return None


def is_frameshifted(data: Dict, pos: int) -> bool:
    """Check if the NT mutation is a frameshift
    deletion: nucAbs begin position = deletion end pos
    insertion: nucAbs begin position = insertion pos +1.
    The pos is already precalculated.
    """
    for frameshift in data.get("frameShifts", []):
        if frameshift["nucAbs"][0]["begin"] == pos:
            # print("frameshifted deteded", frameshift)
            return 1
    return 0


def process_nt_mutations(
    data: Dict, reference_acc: str, reference_seq: str
) -> List[Dict[str, Any]]:
    """
    Process nucleotide (NT) mutations from Nextclade sample data and create initial mutation records.

    This function parses substitutions, deletions, and insertions from the input data,
    constructs a list of NT mutation dictionaries, and assigns unique IDs and parent-child relationships.

    Steps:
    1. Initialize an empty list for mutations and set the starting ID counter.
    2. Parse all nucleotide substitutions:
        - For each substitution, create a mutation record with reference, position, alternate base, and label.
        - Mark as type 'nt' and set frameshift to 0.
        - Store the NT position for later AA mapping.
    3. Parse all nucleotide deletions:
        - For each deletion, extract the reference sequence for the deleted region.
        - Set the start and end positions, alternate as empty string, and label as a deletion.
        - Determine if the deletion causes a frameshift using `is_frameshifted`.
        - Store the NT position for later AA mapping.
    4. Parse all nucleotide insertions:
        - For each insertion, extract the reference base at the insertion site.
        - Set the start and end positions, alternate as the inserted sequence, and label as an insertion.
        - Determine if the insertion causes a frameshift using `is_frameshifted`.
        - Store the NT position for later AA mapping.
    5. Sort all NT mutations by their start position.
    6. Assign unique IDs and set each mutation's parent_id to its own ID.
    7. Return the list of mutation records and the next available ID.

    Args:
        data (Dict): Nextclade sample data.
        reference_acc (str): Reference accession string.
        reference_seq (str): Reference nucleotide sequence.

    Returns:
        Tuple[List[Dict[str, Any]], int]: List of processed NT mutation records and the next available ID.
    """
    mutations = []
    id_counter = 1

    # Process substitutions
    for sub in data.get("substitutions", []):
        mut = {
            "id": id_counter,
            "ref": sub["refNuc"],
            "start": sub["pos"],
            "end": sub["pos"] + 1,
            "alt": sub["qryNuc"],
            "reference_acc": reference_acc,
            "label": f"{sub['refNuc']}{sub['pos'] + 1}{sub['qryNuc']}",
            "type": "nt",
            "frameshift": 0,
            "nt_pos": sub["pos"],  # Store for AA mapping
        }
        mutations.append(mut)

    # Process deletions
    for deletion in data.get("deletions", []):
        mut = {
            "id": id_counter,
            "ref": reference_seq[
                int(deletion["range"]["begin"]) : int(deletion["range"]["end"])
            ],
            "start": deletion["range"]["begin"],
            "end": deletion["range"]["end"] + len(deletion.get("refNuc", "")),
            "alt": "",
            "reference_acc": reference_acc,
            "label": f"del:{deletion['range']['begin'] + 1}-{deletion['range']['end'] + len(deletion.get('refNuc', ''))}",
            "type": "nt",
            "frameshift": is_frameshifted(data, deletion["range"]["end"]),
            "nt_pos": deletion["range"]["begin"],
        }
        mutations.append(mut)

    # Process insertions
    for insertion in data.get("insertions", []):
        pos = int(insertion["pos"])
        ref_base = reference_seq[pos : pos + 1]
        mut = {
            "id": id_counter,
            "ref": ref_base,
            "start": pos,
            "end": pos + 1,
            "alt": ref_base + insertion["ins"],
            "reference_acc": reference_acc,
            "label": f"{ref_base}{pos + 1}{ref_base}{insertion['ins']}",
            "type": "nt",
            "frameshift": is_frameshifted(data, pos + 1),
            "nt_pos": pos,
        }
        mutations.append(mut)

    # Sort NT mutations by position
    mutations = sorted(mutations, key=lambda x: x["start"])

    # Update parent_id for NT mutations
    # Assign IDs and parent_ids to NT mutations
    for mut in mutations:
        mut["id"] = id_counter
        mut["parent_id"] = id_counter
        id_counter += 1

    return mutations, id_counter


def process_aa_mutations(  # noqa: C901
    data: Dict, nt_mutations: List[Dict], start_id: int
) -> List[Dict[str, Any]]:
    """
    Process amino acid (AA) mutations and link them to nucleotide (NT) mutations.

    This function takes Nextclade sample data, a list of NT mutations, and a starting ID,
    and returns a list of AA mutation dictionaries with parent-child relationships to NT mutations.

    Steps:
    1. Build a mapping from NT positions to mutation IDs (`nt_pos_to_id`).
    2. Parse the AA mutation mapping (`nucToAaMuts`) to group AA deletions by gene and position.
    3. Merge adjacent AA deletions, tracking all underlying NT positions (`nt_pos_list`) for robust parent_id mapping.
    4. Parse AA insertions from the input.
    5. Build a position mapping from `aaChangesGroups` for use in insertion and SNP mapping.
    6. For each merged AA deletion:
        - Attempt to find a parent NT mutation by searching all merged `nt_pos` values with small offsets.
        - If not found, attempt to map via frameshift information.
        - Construct the AA deletion mutation record.
    7. For each regular AA mutation (non-deletion):
        - Map to parent NT mutation by position.
        - Handle insertions and SNPs, constructing the mutation record.
    8. Handle any remaining insertions not already mapped.
    9. Combine AA mutations with identical attributes, merging their parent_ids.
    10. Return the final list of AA mutation records.

    Args:
        data (Dict): Nextclade sample data.
        nt_mutations (List[Dict]): List of nucleotide mutation records.
        start_id (int): Starting ID for AA mutations.

    Returns:
        List[Dict[str, Any]]: List of processed AA mutation records, each with parent_id linkage.
    """
    aa_mutations = []
    id_counter = start_id
    # "nucToAaMuts" shows a nucleotide mutation possiton belong to which AA mutation
    nuc_to_aa = {int(k): v for k, v in data.get("nucToAaMuts", {}).items()}
    # Create position mapping from all NT mutations that we construct from
    # previous (nt_mutations)
    nt_pos_to_id = {mut["nt_pos"]: mut["id"] for mut in nt_mutations}
    # print("---nt_pos_to_id---")
    # print(nt_pos_to_id)

    # Create a mapping of NT mutation IDs to their frameshift status
    frameshift_nt_ids = {
        mut["id"]: mut["frameshift"]
        for mut in nt_mutations
        if mut.get("frameshift", 0) != 0
    }

    # ----------------- Create AA Deletion
    deletion_groups = {}

    # First pass: collect and group deletions
    for nt_pos, aa_info_list in nuc_to_aa.items():
        nt_pos = int(nt_pos)
        # sometimes aa_info_list contains one more range
        for aa_info in aa_info_list:
            if aa_info["qryAa"] == "-":  # This is a deletion
                cds_name = aa_info["cdsName"]
                pos = aa_info["pos"]
                if cds_name not in deletion_groups:
                    deletion_groups[cds_name] = {}
                if pos not in deletion_groups[cds_name]:
                    deletion_groups[cds_name][pos] = {
                        "ref": aa_info["refAa"],
                        "positions": set([pos]),
                        "nt_pos": nt_pos,
                    }
                else:
                    deletion_groups[cds_name][pos]["positions"].add(pos)

    # Second pass: merge adjacent deletions
    merged_deletions = {}
    for cds_name, positions in deletion_groups.items():
        sorted_positions = sorted(positions.keys())
        current_group = None

        for pos in sorted_positions:
            if current_group is None:
                current_group = {
                    "start": pos,
                    "end": pos + 1,
                    "ref": positions[pos]["ref"],
                    "nt_pos": positions[pos]["nt_pos"],
                    "nt_pos_list": [positions[pos]["nt_pos"]],  # <-- Track all nt_pos
                }
            elif pos == current_group["end"]:  # keep merging
                current_group["end"] = pos + 1
                current_group["ref"] += positions[pos]["ref"]
                current_group["nt_pos_list"].append(positions[pos]["nt_pos"])
            else:
                if cds_name not in merged_deletions:
                    merged_deletions[cds_name] = []
                merged_deletions[cds_name].append(current_group)
                # init for next del mutation.
                current_group = {
                    "start": pos,
                    "end": pos + 1,
                    "ref": positions[pos]["ref"],
                    "nt_pos": positions[pos]["nt_pos"],
                    "nt_pos_list": [positions[pos]["nt_pos"]],
                }
        # handle the last
        if current_group:
            if cds_name not in merged_deletions:
                merged_deletions[cds_name] = []
            merged_deletions[cds_name].append(current_group)
    # print("---merged_deletions---")
    # print(merged_deletions)

    # -----------------  Create AA Insertion
    # we collect the insertion information from
    # "aaInsertions"
    aa_insertions = {}
    for insertion in data.get("aaInsertions", []):
        key = f"{insertion['cds']}_{insertion['pos']}"  # pos to match positions
        aa_insertions[key] = insertion["ins"]

    # print("---aa_insertions---")
    # print(aa_insertions)
    # ----------------- Start mapping -----------------
    # Create a position mapping from aaChangesGroups.
    # The aaChangesGroups will help us identify
    # AA changes related to insertion and deletions to mapping nucPos
    # NOTE: The position in aaInsertions is 0-based,
    # while in aaChangesGroups it is 1-based (label representation).

    position_mapping = {}
    for group in data.get("aaChangesGroups", []):
        cds_name = group["name"]
        for change in group.get("changes", []):
            aa_pos = change["pos"] - 1  # convert to same based
            key = f"{cds_name}_{aa_pos}"
            position_mapping[key] = {
                "aaPos": change["pos"],
                "nucPos": change["nucPos"],
                "refAa": change["refAa"],
                "qryAa": change["qryAa"],
                "nucRanges": int(change["nucRanges"][0]["end"])
                - int(change["nucRanges"][0]["begin"]),
                "nucRanges_ov": change["nucRanges"][0]["end"]
                - change["nucRanges"][0]["begin"],
            }

    # Process deletions
    for cds_name, deletions in merged_deletions.items():
        for del_info in deletions:
            # handle del label (one deleted position ---> del:69 or multiple positions ---> del:68-69)
            label = (
                f"del:{del_info['start'] + 1}"
                if del_info["start"] + 1 == del_info["end"]
                else f"del:{del_info['start'] + 1}-{del_info['end']}"
            )
            # NOTE: the current solution for now.
            # The position in "nucToAaMuts" may differ for some deletion positions compared to
            # "aaChangesGroups"."changes." However, "aaChangesGroups"."changes" always
            # contains refTriplet and qryTriplet, which use a range of three nucleotides.
            # Therefore, we should try offset positions of (0, 1, 2, 3, -1, -2, -3)
            # relative to nt_pos_list to find the valid parent_id.
            parent_id = None
            for nt_pos in del_info["nt_pos_list"]:
                for offset in [0, 1, 2, 3, -1, -2, -3]:
                    if nt_pos + offset in nt_pos_to_id:
                        parent_id = nt_pos_to_id[nt_pos + offset]
                        break
                if parent_id is not None:
                    break

            # for the case of framshift deletion
            if parent_id is None:
                for frameshift in data.get("frameShifts", []):
                    # find deletion mapping position
                    for deletion in data.get("deletions", []):
                        if frameshift["nucAbs"][0]["begin"] == deletion["range"]["end"]:
                            # find parent ID
                            parent_id = nt_pos_to_id.get(
                                deletion["range"]["begin"], None
                            )
                            break

            frameshift_status = frameshift_nt_ids.get(parent_id, 0)
            mut = {
                "id": id_counter,
                "ref": del_info["ref"],
                "start": del_info["start"],
                "end": del_info["end"],
                "alt": "",
                "reference_acc": cds_name,
                "label": label,
                "type": "cds",
                "frameshift": frameshift_status,
                "parent_id": parent_id,
            }
            aa_mutations.append(mut)
            id_counter += 1

    # Process regular mutations (non-deletions)
    for nt_pos, aa_info_list in nuc_to_aa.items():
        nt_pos = int(nt_pos)
        for aa_info in aa_info_list:
            if aa_info["qryAa"] == "-":  # Skip deletions as they're already processed
                continue

            parent_id = nt_pos_to_id.get(nt_pos, None)
            if parent_id is None:
                continue

            # Check position and position-1+1 for insertions
            insertion_keys = [
                f"{aa_info['cdsName']}_{aa_info['pos']}",
                f"{aa_info['cdsName']}_{aa_info['pos'] - 1}",
                f"{aa_info['cdsName']}_{aa_info['pos'] + 1}",
            ]

            # Find matching insertion key and remove it so it won't be used again,
            # because we know which insertion mutations didnt list in nucToAaMuts
            matching_key = None
            for key in insertion_keys:
                if key in aa_insertions:
                    matching_key = key
                    inserted_aa = aa_insertions.pop(key)
                    break

            if matching_key:
                position_info = position_mapping.get(matching_key)
                # Check if this is a termination followed by insertion (*) or regular AA followed by insertion
                if position_info["qryAa"] == "*":
                    alt = inserted_aa
                else:
                    alt = position_info["qryAa"] + inserted_aa
                frameshift_status = frameshift_nt_ids.get(parent_id, 0)
                mut = {
                    "id": id_counter,
                    "ref": aa_info["refAa"],
                    "start": aa_info["pos"],
                    "end": aa_info["pos"] + 1,
                    "alt": alt,
                    "reference_acc": aa_info["cdsName"],
                    "label": f"{aa_info['refAa']}{aa_info['pos']}{alt}",
                    "type": "cds",
                    "frameshift": frameshift_status,
                    "parent_id": parent_id,
                }
            else:  # snp
                frameshift_status = frameshift_nt_ids.get(parent_id, 0)
                mut = {
                    "id": id_counter,
                    "ref": aa_info["refAa"],
                    "start": aa_info["pos"],
                    "end": aa_info["pos"] + 1,
                    "alt": aa_info["qryAa"],
                    "reference_acc": aa_info["cdsName"],
                    "label": f"{aa_info['refAa']}{aa_info['pos'] + 1}{aa_info['qryAa']}",
                    "type": "cds",
                    "frameshift": frameshift_status,
                    "parent_id": parent_id,
                }

            aa_mutations.append(mut)
            id_counter += 1

    # handle the remaining insertion.
    for key, inserted_aa in aa_insertions.items():
        # split _ key to cds_name and pos
        cds_name, pos = key.split("_")

        insertion_keys = [
            f"{cds_name}_{pos}",
            f"{cds_name}_{int(pos) - 1}",
            f"{cds_name}_{int(pos) + 1}",
        ]
        for matching_key in insertion_keys:
            position_info = position_mapping.get(matching_key)
            if position_info is None:
                continue
            if position_info["qryAa"] == "*":
                alt = inserted_aa
            else:
                alt = position_info["qryAa"] + inserted_aa

            # find parent ID again
            nt_pos = (
                position_info["nucPos"] + position_info["nucRanges"] - 1
            )  # -1 to 0-based
            parent_id = nt_pos_to_id.get(nt_pos, None)
            if parent_id is None:
                # This time, if it doesn't exist, we cannot do anything.
                continue
            frameshift_status = frameshift_nt_ids.get(parent_id, 0)
            mut = {
                "id": id_counter,
                "ref": position_info["refAa"],
                "start": position_info["aaPos"],
                "end": position_info["aaPos"] + 1,
                "alt": alt,
                "reference_acc": cds_name,
                "label": f"{position_info['refAa']}{position_info['aaPos'] + 1}{alt}",
                "type": "cds",
                "frameshift": frameshift_status,
                "parent_id": parent_id,
            }
            aa_mutations.append(mut)
            id_counter += 1

    # combine the parent_id with the same AA mutations (aa_mutations)
    # for example,
    # 91	D	2	3	L	QHD43423.2	D3L	cds	0	55
    # 92	D	2	3	L	QHD43423.2	D3L	cds	0	56
    # 93	D	2	3	L	QHD43423.2	D3L	cds	0	57
    # will be combined to
    # 91	D	2	3	L	QHD43423.2	D3L	cds	0	55,56,57
    # Create a dictionary to group mutations by their key attributes
    grouped_mutations = {}

    for mutation in aa_mutations:
        # Create a key tuple with all attributes except id and parent_id and frameshift
        key = (
            mutation["ref"],
            mutation["start"],
            mutation["end"],
            mutation["alt"],
            mutation["reference_acc"],
            mutation["label"],
            mutation["type"],
        )

        if key not in grouped_mutations:
            # For new entries, keep the frameshift status
            grouped_mutations[key] = {
                **mutation,
                "parent_id": str(mutation["parent_id"]),
                "frameshift": mutation["frameshift"],  # Keep original frameshift
            }
        else:
            # Append parent_id to existing mutation
            grouped_mutations[key]["parent_id"] += f",{mutation['parent_id']}"
            # If any mutation has frameshift=1, set the combined mutation to frameshift=1
            if mutation["frameshift"] == 1:
                grouped_mutations[key]["frameshift"] = 1

    # Convert back to list
    final_combined_mutations = list(grouped_mutations.values())

    return final_combined_mutations


def process_single_sample(  # noqa: C901
    sample_data: Dict,
    reference_acc: str,
    gene_to_cds: Dict[str, Any],
    reference_seq: str,
    output_dir: str = None,
    output_file: str = None,
    output_parquet_file: str = None,
    debug: bool = False,
) -> None:
    """Process a single sample and create its .var file,
    the interface for sonar-cli
    """
    try:
        # Get sample name/id
        sample_id = sample_data.get("seqId", "unknown")
        # Process NT mutations
        nt_mutations, next_id = process_nt_mutations(
            sample_data, reference_acc, reference_seq
        )

        # Process AA mutations
        aa_mutations = process_aa_mutations(sample_data, nt_mutations, next_id)
        #  map Gene name with Gene ID in the database
        for mutation in aa_mutations:
            gene_symbol = mutation.get("reference_acc")
            cds_accession = gene_to_cds.get((gene_symbol, reference_acc))

            # Add the found CDS accession back to the mutation dict
            mutation["reference_acc"] = cds_accession

        # Combine and clean up mutations
        all_mutations = nt_mutations + aa_mutations
        for mut in all_mutations:
            mut.pop("nt_pos", None)

        # check if there is empty parent_id
        # Log for debugging
        for mut in all_mutations:
            if mut.get("parent_id") is None:
                LOGGER.warning(
                    f" {sample_id}: MutationID {mut['id']} has no parent_id, see {output_file} "
                )

        if output_dir is not None:
            # Create output filename
            output_file = os.path.join(output_dir, f"{sample_id}.var")

        # Create DataFrame
        df = pd.DataFrame(all_mutations)
        # Ensure correct column order and types
        df["parent_id"] = df["parent_id"].astype(str)
        # NOTE: tmp remove row where parent_id where is none
        # df = df[df["parent_id"].notna()]
        # remove parent_id where is 'None'
        # df = df[(df["parent_id"] != "None") & (df["parent_id"] != "nan")]

        if debug:
            # Save to TSV file
            if output_file:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
            df.to_csv(output_file, sep="\t", index=False)

        if output_parquet_file:
            os.makedirs(os.path.dirname(output_parquet_file), exist_ok=True)
            df.to_parquet(
                output_parquet_file,
                compression="zstd",
                compression_level=10,
                index=False,
            )
        return True
    except Exception as e:
        print(f"Error processing sample {sample_id}: {str(e)}")
        return False


def create_var_files_from_json_parallel(
    input_json: str,
    output_dir: str,
    reference_acc: str,
    reference_seq: str,
    n_workers: int = 4,
) -> None:
    """Create .var files from Nextclade JSON output using parallel processing"""

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Read all samples from JSON file
    samples = read_nextclade_json(input_json)
    if not samples:
        print("Error: No samples found in JSON file")
        return

    print(f"Processing {len(samples)} samples using {n_workers} workers...")

    # Prepare arguments for each job
    # Create output filename

    job_args = [
        (sample, reference_acc, reference_seq, output_dir) for sample in samples
    ]

    # Define worker function
    def working_job(*args):
        sample, ref_acc, ref_seq, out_dir = args
        return process_single_sample(sample, ref_acc, ref_seq, out_dir)

    # Initialize MPIRE worker pool
    with WorkerPool(n_jobs=n_workers) as pool:
        # Process samples in parallel
        results = pool.map(working_job, job_args, progress_bar=True)

        # Count successful processes
        successful = sum(1 for result in results if result)
        print(f"Successfully processed {successful} out of {len(samples)} samples")


def create_var_file_from_json(
    input_json: str, output_file: str, reference_acc: str, reference_seq: str
) -> None:
    """Create .var file from Nextclade JSON output"""
    # Read JSON data
    data = read_nextclade_json(input_json)
    if not data:
        print("Error: No data found in JSON file")
        return

    # Process NT mutations
    nt_mutations, next_id = process_nt_mutations(data, reference_acc, reference_seq)

    # Process AA mutation
    aa_mutations = process_aa_mutations(data, nt_mutations, next_id)

    # Combine and clean up mutations
    all_mutations = nt_mutations + aa_mutations

    # Remove temporary nt_pos field
    for mut in all_mutations:
        mut.pop("nt_pos", None)

    # TODO: map Gene name with Gene ID in the database

    # Create DataFrame
    # parent_id is id and it is int.
    # id ref	start	end	alt	reference_acc	label	type parent_id
    df = pd.DataFrame(all_mutations)

    # Save to TSV file
    df.to_csv(output_file, sep="\t", index=False)
