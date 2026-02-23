import gzip
import os
from pathlib import Path
import pickle
import shutil

from Bio import SeqIO
import sourmash
from sourmash import signature
from sourmash.index import LinearIndex
from sourmash.logging import set_quiet

# Set quiet mode for cleaner output
set_quiet(True)


# ===== Helper Functions =====


def _create_minhash(sequence: str, ksize: int, scaled: int):
    """Create a MinHash sketch for a given sequence."""
    mh = sourmash.MinHash(n=0, ksize=ksize, scaled=scaled)
    mh.add_sequence(sequence, force=True)
    return mh


def _create_signature(sequence: str, name: str, ksize: int, scaled: int):
    """Create a Sourmash signature for a given sequence."""
    mh = _create_minhash(sequence, ksize, scaled)
    return signature.SourmashSignature(mh, name=name)


def _load_db(db_path: str):
    """Load a Sourmash LinearIndex from a file."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at {db_path}")

    with open(db_path, "rb") as db_file:
        return pickle.load(db_file)


def _search_signature(db, sig, threshold: float = 0.01):
    """Search a signature against a database."""
    return db.search(sig, threshold=threshold)


# ===== Main Interface with sonar-cli =====


def create_cluster_db(records: dict, db_name: str, ksize=11, scaled=1):
    index = LinearIndex()

    for accession, data in records.items():
        sig = _create_signature(data["sequence"], accession, ksize, scaled)
        index.insert(sig)

    with open(db_name, "wb") as db_file:
        pickle.dump(index, db_file)

    # print(f"Database saved to {db_name}")


def perform_search(fasta_file: str, db_path: str, ksize: int = 11, scaled: int = 1):
    db = _load_db(db_path)
    best_alignments = {}
    decompressed_file = None
    # Check if the file is compressed with .gz, .xz, or .zip
    if fasta_file.endswith(".gz"):
        decompressed_file = fasta_file.rstrip(".gz")
        with gzip.open(fasta_file, "rb") as in_f:
            with open(decompressed_file, "wb") as out_f:
                shutil.copyfileobj(in_f, out_f)
        fasta_file = decompressed_file
    elif fasta_file.endswith(".xz"):
        decompressed_file = fasta_file.rstrip(".xz")
        os.system(f"xz -d -c {fasta_file} > {decompressed_file}")
        fasta_file = decompressed_file
    elif fasta_file.endswith(".zip"):
        decompressed_file = fasta_file.rstrip(".zip")
        with shutil.ZipFile(fasta_file, "r") as zip_ref:
            zip_ref.extractall(Path(fasta_file).parent)
            decompressed_file = str(
                Path(fasta_file).with_suffix("")
            )  # Assuming single file in zip
        fasta_file = decompressed_file

    for record in SeqIO.parse(fasta_file, "fasta"):
        sig = _create_signature(str(record.seq), record.id, ksize, scaled)
        results = _search_signature(db, sig)

        if results:
            best_match = max(results, key=lambda x: x[0])  # highest similarity
            similarity_score, found_sig, _ = best_match
            best_alignments[record.id] = found_sig.name
        else:
            raise ValueError(
                f"No significant matches found for sequence {record.id}. Cannot assign the segments."
            )

    # write best_alignments to a file tsv format
    # in the same directory as the db
    db_dir = Path(db_path).parent
    output_file = db_dir / f"{Path(db_path).stem}_best_alignments.tsv"
    with open(output_file, "w") as out_file:
        out_file.write("Sample_ID\tBest_Match\n")
        for sample_id, best_match in best_alignments.items():
            out_file.write(f"{sample_id}\t{best_match}\n")
            # print(f"Best match for {sample_id}: {best_match}")

    # rm the copy file
    if decompressed_file and os.path.exists(decompressed_file):
        os.remove(decompressed_file)
    return best_alignments


# ===== Test Functions =====


def create_signatures_fromGB(genbank_files, ksize=11, scaled=1):
    """Create MinHash signatures from GenBank files and return a LinearIndex."""
    index = LinearIndex()

    for gb_file in genbank_files:
        for record in SeqIO.parse(gb_file, "genbank"):
            sig = _create_signature(str(record.seq), record.id, ksize, scaled)
            index.insert(sig)
            print(f"Signature created for {record.id} from {gb_file}")

    return index


def search_sequence(sample_fasta: str, db: LinearIndex, ksize=11, scaled=1):
    """Search sample sequences for similarity to database entries."""
    for record in SeqIO.parse(sample_fasta, "fasta"):
        sig = _create_signature(str(record.seq), record.id, ksize, scaled)
        results = _search_signature(db, sig)

        if results:
            print(f"Sample {record.id} matches:")
            for similarity, found_sig, _ in results:
                print(f"  - {found_sig} with similarity {similarity}")
        else:
            print(f"Sample {record.id} has no significant matches.")


if __name__ == "__main__":
    # Example Usage for testing
    # Create a database from GenBank files
    # and then perform a search with a sample FASTA file.
    genbank_files = [
        "/mnt/c/works/sonar-cli/test-data/MN908947.nextclade.gb",
        "/mnt/c/works/influ/InfluenzaA_H1N1_seg1.gb",
        "/mnt/c/works/influ/InfluenzaA_H1N1_seg2.gb",
        "/mnt/c/works/influ/InfluenzaA_H1N1_seg3.gb",
        "/mnt/c/works/influ/InfluenzaA_H1N1_seg4.gb",
        "/mnt/c/works/influ/InfluenzaA_H1N1_seg5.gb",
        "/mnt/c/works/influ/InfluenzaA_H1N1_seg6.gb",
        "/mnt/c/works/influ/InfluenzaA_H1N1_seg7.gb",
        "/mnt/c/works/influ/InfluenzaA_H1N1_seg8.gb",
    ]

    db = create_signatures_fromGB(genbank_files, ksize=9)

    sample_fasta = "/mnt/c/works/influ/H1N1.sequences.fasta"
    search_sequence(sample_fasta, db, ksize=9)
