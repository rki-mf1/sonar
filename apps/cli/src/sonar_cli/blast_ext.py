import csv
from datetime import datetime
import subprocess

from Bio import SeqIO
from Bio.Application import ApplicationError
from Bio.Blast import NCBIXML
from Bio.Blast.Applications import NcbiblastnCommandline
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord


def extract_id_between_pipes(header):
    try:
        # Split the header by '|' and return the element in the middle
        parts = header.split("|")
        if len(parts) >= 3:
            return parts[1]
        else:
            raise ValueError(
                "Header does not contain the expected format with two pipe characters."
            )
    except Exception as e:
        print(f"Error: {e}")
        raise


def modify_fasta_headers(input_path, output_path):
    # Read the input FASTA file and modify the headers
    modified_records = []
    with open(input_path, "r") as input_handle:
        for record in SeqIO.parse(input_handle, "fasta"):
            # Extract the accession ID (the part before the first space in the description)
            accession_id = record.description.split()[0]
            # Update the record ID and description
            record.id = accession_id
            record.description = ""
            modified_records.append(record)

    # Write the modified records to the output FASTA file
    with open(output_path, "w") as output_handle:
        SeqIO.write(modified_records, output_handle, "fasta")
    print(f"Modified FASTA headers saved to '{output_path}'.")


# def modified_record_fromGenbank(records):
#    for record in records:
#        # Clear the description
#        record.description = ""
#        yield record


# Load and parse the GenBank file
def load_genbank_file(file_path):
    return list(SeqIO.parse(file_path, "genbank"))


def parse_genbank_files(file_paths):
    records = []
    for file_path in file_paths:
        records.extend(list(SeqIO.parse(file_path, "genbank")))
    return records


def append_to_existing_db(new_records, db_name):
    fasta_file = f"{db_name}.fasta"
    with open(fasta_file, "a") as output_handle:
        SeqIO.write(new_records, output_handle, "fasta")
    print(f"Appended {len(new_records)} records to {fasta_file}")


# def create_blast_db_Genbank(records, db_name):
#     fasta_file = f"{db_name}.fasta"
#     with open(fasta_file, "w") as output_handle:
#         SeqIO.write(modified_record_fromGenbank(records), output_handle, "fasta")

#     # Create a BLAST database
#     makeblastdb_cmd = [
#         "makeblastdb",
#         "-in",
#         fasta_file,
#         "-dbtype",
#         "nucl",
#         "-out",
#         db_name,
#         "-parse_seqids",
#     ]
#     subprocess.run(makeblastdb_cmd)


def modified(records):
    seq_records = []
    for accession, data in records.items():
        seq_record = SeqRecord(Seq(data["sequence"]), id=accession, description="")
        seq_records.append(seq_record)
    return seq_records


def create_blast_db(records: dict, db_name: str):
    fasta_file = f"{db_name}.fasta"

    with open(fasta_file, "w") as output_handle:
        SeqIO.write(modified(records), output_handle, "fasta")

    # Create a BLAST database
    makeblastdb_cmd = [
        "makeblastdb",
        "-in",
        fasta_file,
        "-dbtype",
        "nucl",
        "-out",
        db_name,
        "-parse_seqids",
    ]
    subprocess.run(makeblastdb_cmd)


def rebuild_blast_db(fasta_file, db_name):
    makeblastdb_cmd = [
        "makeblastdb",
        "-in",
        fasta_file,
        "-dbtype",
        "nucl",
        "-out",
        db_name,
        "-parse_seqids",  # enable to search ID
    ]
    subprocess.run(makeblastdb_cmd)
    print(f"Rebuilt BLAST database '{db_name}'.")


def perform_blast_search(fasta_file, db_name, output_file):
    blastn_cline = NcbiblastnCommandline(
        query=fasta_file,
        db=db_name,
        evalue=0.001,
        outfmt=6,
        max_target_seqs=1,
        out=output_file,
        # outfmt=ุุ6'qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore'
    )
    stdout, stderr = blastn_cline()
    return output_file


# def parse_blast_results(output_file):
#     with open(output_file) as result_handle:
#         blast_records = NCBIXML.parse(result_handle)
#         for blast_record in blast_records:
#             print("---------------")
#             for alignment in blast_record.alignments:
#                 for hsp in alignment.hsps:
#                     print("****Alignment****")
#                     print(f"sequence: {alignment.title}")
#                     print(f"length: {alignment.length}")
#                     print(f"e value: {hsp.expect}")
#                     print(f"score: {hsp.score}")
#                     print(hsp.query[0:75] + "...")
#                     print(hsp.match[0:75] + "...")
#                     print(hsp.sbjct[0:75] + "...")
def parse_blast_results(output_file):
    best_alignments = {}
    with open(output_file) as result_handle:
        blast_records = NCBIXML.parse(result_handle)
        for blast_record in blast_records:
            print(blast_record.__dict__)
            query_id = blast_record.query
            print(f"-------- {query_id}-------")
            if blast_record.alignments:

                best_alignment = blast_record.alignments[0]
                best_hsp = best_alignment.hsps[0]
                print(best_alignment.__dict__)
                best_alignments[query_id] = extract_id_between_pipes(
                    best_alignment.hit_id
                )

                # use best_alignment.accession, the version is missing
                # best_alignment.hit_id
                print("****Alignment****")
                print(f"sequence: {best_alignment.title}")
                print(f"length: {best_alignment.length}")
                print(f"e value: {best_hsp.expect}")
                print(f"score: {best_hsp.score}")
                print(f"Best Hit Accession ID: {best_alignment.accession}")
                # print(best_hsp.query[0:75] + "...")
                # print(best_hsp.match[0:75] + "...")
                # print(best_hsp.sbjct[0:75] + "...")
    return best_alignments


def parse_blast_results_tsv(output_file):
    best_alignments = {}
    with open(output_file, "r") as tsvfile:
        tsvreader = csv.reader(tsvfile, delimiter="\t")
        for row in tsvreader:

            (
                query_id,
                subject_id,
                identity,
                alignment_length,
                mismatches,
                gap_opens,
                q_start,
                q_end,
                s_start,
                s_end,
                e_value,
                bit_score,
            ) = row
            best_alignments[query_id] = subject_id

            # Print alignment details
            print(f"-------- {query_id} -------")
            print("****Alignment****")
            print(f"Subject ID: {subject_id}")
            print(f"Identity: {identity}")
            # print(f"Alignment Length: {alignment_length}")
            # print(f"Mismatches: {mismatches}")
            # print(f"Gap Opens: {gap_opens}")
            # print(f"Query Start: {q_start}")
            # print(f"Query End: {q_end}")
            # print(f"Subject Start: {s_start}")
            # print(f"Subject End: {s_end}")
            # print(f"E-value: {e_value}")
            print(f"Bit Score: {bit_score}")
            print()

    return best_alignments


def perform_blast_search_tsv_from_memory(fasta_file, db_name) -> dict:
    # The smaller the E-value, the better the match.
    fasta_file = "/mnt/c/works/influ/mix.seq.fasta"
    try:
        cline = NcbiblastnCommandline(
            query=fasta_file,
            db=db_name,
            evalue=0.000001,
            outfmt=6,
            max_target_seqs=5,
            out="-",
        )
        print(cline)
        output = cline()[0].strip()
        rows = [line.split() for line in output.splitlines()]
        best_alignments = {}

        for row in rows:
            if len(row) < 12:
                continue  # Skip incomplete rows
            (
                query_id,
                subject_id,
                identity,
                alignment_length,
                mismatches,
                gap_opens,
                q_start,
                q_end,
                s_start,
                s_end,
                e_value,
                bit_score,
            ) = row
            best_alignments[query_id] = subject_id

            # Print alignment details
            # print(f"-------- {query_id} -------")
            # print("****Alignment****")
            # print(f"Subject ID: {subject_id}")
            # print(f"Identity: {identity}")
            # print(f"Bit Score: {bit_score}")
            # print()
        return best_alignments
    except ApplicationError as e:
        print(f"Error running BLAST: {e}")
        print(f"Command: {e.cmd}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise


def update_fasta_headers(fasta_file, best_alignments, output_file):
    records = list(SeqIO.parse(fasta_file, "fasta"))
    for record in records:
        query_id = record.id
        if query_id in best_alignments:

            ref_id = best_alignments[query_id]

            record.id = query_id  # = f"assigned_refID={ref_id}"
            record.description = f"molecule={ref_id}"
    SeqIO.write(records, output_file, "fasta")
    print(f"Updated headers in FASTA file saved to '{output_file}'.")


def write_best_aln_csv(best_alignments, output_match_file):
    with open(output_match_file, "w") as f:
        for key in best_alignments.keys():
            f.write("%s,%s\n" % (key, best_alignments[key]))


if __name__ == "__main__":

    # genbank_file_path = '/mnt/c/works/sonar/test-data/MN908947.nextclade.gb'
    # records = load_genbank_file(genbank_file_path)
    # print(f"Loaded {len(records)} records from the GenBank file.")
    # print(records)

    # uploaded_fasta_file = '/mnt/c/works/covid-19-new/covid19.180.fasta'
    uploaded_fasta_file = "/mnt/c/works/influ/InfuA.mix.fasta"
    input_fasta_file = "/mnt/c/works/tmp/mix.seq.modified.fasta"
    output_blast_results = "/mnt/c/works/tmp/blast_results.tsv"

    updated_fasta_file = "/mnt/c/works/tmp/updated_fasta_with_refID.fasta"
    output_match_file = "/mnt/c/works/tmp/output_match_file.csv"
    db_name = "/mnt/c/works/tmp/genbank_db"
    # create_blast_db(records, db_name)
    # print(f"BLAST database '{db_name}' created.")

    new_genbank_files = [
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

    new_records = parse_genbank_files(new_genbank_files)
    create_blast_db(new_records, db_name)
    # rebuild_blast_db(f"{db_name}.fasta", db_name)

    modify_fasta_headers(uploaded_fasta_file, input_fasta_file)
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    # perform_blast_search(uploaded_fasta_file, db_name, output_file)
    # print(f"Similarity search results saved to '{output_file}'.")
    # parse_blast_results(output_file)

    # -------------------------------------
    # perform_blast_search(input_fasta_file, db_name, output_blast_results)
    # print(f"Similarity search results saved to '{output_blast_results}'.")
    # # Parse BLAST results and get best alignments
    # best_alignments = parse_blast_results_tsv(output_blast_results)
    # -------------------------------------

    best_alignments = perform_blast_search_tsv_from_memory(input_fasta_file, db_name)

    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    # Update FASTA headers with best alignment accession IDs
    # update_fasta_headers(input_fasta_file, best_alignments, updated_fasta_file)
    # best_hit = blast_record.alignments[0] # Access the first (best) alignment
    # best_hsp = best_hit.hsps[0] ## Access the first high-scoring segment pair
    # print("Best Hit Title:", best_hit.title)
    # print("Best Hit Subject Sequence:", best_hsp.sbjct)
    with open(output_match_file, "w") as f:
        for key in best_alignments.keys():
            f.write("%s,%s\n" % (key, best_alignments[key]))
    # blastdbcmd -db genbank_db  -entry all -outfmt "%a"
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
