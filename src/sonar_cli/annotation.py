import os
import subprocess
import sys
from typing import Optional

from sonar_cli.cache import sonarCache
from sonar_cli.logging import LoggingConfigurator

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()


class Annotator:
    def __init__(
        self,
        annotator_exe_path=None,
        SNPSIFT_exe_path=None,
        VCF_ONEPERLINE_PATH=None,
        config_path=None,
        cache: Optional[sonarCache] = None,
    ) -> None:
        # "snpEff/SnpSift.jar"
        self.annotator = annotator_exe_path
        self.SNPSIFT = SNPSIFT_exe_path
        self.VCF_ONEPERLINE_TOOL = VCF_ONEPERLINE_PATH
        self.config_path = config_path
        self.sonar_cache = cache

    def snpeff_annotate(self, input_vcf, output_vcf, database_name):
        if not self.annotator:
            raise ValueError("Annotator executable path is not provided.")
        # Command to annotate using SnpEff
        command = " ".join(
            [f"{self.annotator}", f"{database_name}", f"{input_vcf}", "-noStats"]
        )
        if self.config_path:
            command = command + f" -nodownload -config {self.config_path}"

        try:
            # Run the SnpEff annotation
            with open(output_vcf, "w") as output_file:
                result = subprocess.run(
                    command, shell=True, stdout=output_file, stderr=subprocess.PIPE
                )
            # result = subprocess.run(['java', '-version'], stderr=subprocess.STDOUT)
            if result.returncode != 0:
                LOGGER.error("Output failed with exit code: %s", result.returncode)
                LOGGER.error("Command to reproduce the error: %s", command)

                with open(self.sonar_cache.error_logfile_name, "a+") as writer:
                    writer.write("Fail anno:" + command + "\n")

                LOGGER.error(result.stderr.decode("utf-8").splitlines())

        except subprocess.CalledProcessError as e:
            LOGGER.error("Annotation failed: %s", e)

    def bcftools_filter(self, input_vcf, output_vcf):
        filter_command = f"bcftools view -e 'INFO/ANN=\".\"' {input_vcf} > {output_vcf}"

        # Execute the filter command
        filter_process = subprocess.run(filter_command, shell=True)
        if filter_process.returncode != 0:
            LOGGER.error("Error occurred while filtering the VCF file.")

    def bcftools_split(
        self, input_vcf, output_vcfs=[], map_name_annovcf_dict: dict = {}
    ):
        filtered_vcf = f"{input_vcf}.filtered"
        # Define the command to filter the VCF file
        filter_command = (
            f"bcftools view -e 'INFO/ANN=\".\"' {input_vcf} > {filtered_vcf}"
        )

        # Execute the filter command
        filter_process = subprocess.run(filter_command, shell=True)
        if filter_process.returncode != 0:
            LOGGER.error("Error occurred while filtering the VCF file.")

        # Get the list of sample names from the command output
        sample_names_cmd = f"bcftools query -l {filtered_vcf}"
        sample_names_process = subprocess.run(
            sample_names_cmd, shell=True, capture_output=True, text=True
        )

        if sample_names_process.returncode != 0:
            print("Error occurred while getting sample names.")
            print("Error output:", sample_names_process)
            exit()

        sample_names = sample_names_process.stdout.strip().split()

        # Process each sample
        for sample in sample_names:
            anno_vcf = map_name_annovcf_dict[sample]
            # --no-header suppress the header in VCF output
            cmd = f"bcftools view --exclude-uncalled --no-header --trim-alt-alleles -s {sample} {filtered_vcf} -Oz -o {anno_vcf}"
            process = subprocess.run(cmd, shell=True)

            if process.returncode != 0:
                print(f"Error occurred while processing sample {sample}")

        if os.path.exists(filtered_vcf):
            os.remove(filtered_vcf)

    def bcftools_merge(self, input_vcfs, output_vcf):
        # Loop through each input VCF path
        compressed_vcf_list = []
        for vcf_path in input_vcfs:
            # Compose the commands with the current VCF path
            compressed_vcf = vcf_path + ".gz"
            bgzip_cmd = f"bgzip {vcf_path} -k -f  > {compressed_vcf} "
            tabix_cmd = f"tabix -p vcf {compressed_vcf} "
            compressed_vcf_list.append(compressed_vcf)
            # Execute bgzip command
            result = subprocess.run(bgzip_cmd, shell=True, stderr=subprocess.PIPE)

            # Execute tabix command
            result = subprocess.run(tabix_cmd, shell=True, stderr=subprocess.PIPE)
        # Merge.
        # bcftools = can use --use-header to modify VCF header or reheader command
        full_inputs = " ".join(compressed_vcf_list)
        command = f"bcftools merge {full_inputs} -o {output_vcf}  "
        result = subprocess.run(command, shell=True, stderr=subprocess.PIPE)

        if result.returncode != 0:
            LOGGER.error("Output failed with exit code: %s", result.returncode)
            LOGGER.error(result.stderr.decode("utf-8"))
            LOGGER.error("Input file: %s", input_vcfs)
            LOGGER.error("Output file: %s", output_vcf)
            sys.exit(1)
        return output_vcf

    # def snpeff_transform_output(self, annotated_vcf, output_tsv):
    #     if not self.SNPSIFT:
    #         raise ValueError("SNPSIFT executable path is not provided.")

    #     # Command to transform SnpEff-annotated VCF to TSV
    #     transform_command = [
    #         f"cat {annotated_vcf} | perl {self.VCF_ONEPERLINE_TOOL} | java -jar {self.SNPSIFT} extractFields  -e '.' - 'CHROM' 'POS' 'REF' 'ANN[*].ALLELE' 'ANN[*].EFFECT' 'ANN[*].IMPACT' "
    #     ]

    #     try:
    #         # Run the transformation command
    #         with open(output_tsv, "w") as output_file:
    #             result = subprocess.run(
    #                 transform_command,
    #                 shell=True,
    #                 stdout=output_file,
    #                 stderr=subprocess.PIPE,
    #             )
    #         if result.returncode != 0:
    #             LOGGER.error("Output failed with exit code: %s", result.returncode)
    #             print("Error output:", result.stderr.decode("utf-8"))
    #     except subprocess.CalledProcessError as e:
    #         LOGGER.error("Output transformation failed: %s", e)


# def read_tsv_snpSift(file_path: str) -> pd.DataFrame:
#     """
#     Process the TSV file from SnpSift, deduplicate the ANN[*].EFFECT column,
#     remove values in ANN[*].IMPACT column, and split the records
#     to have one effect per row.
#     Returns the modified DataFrame.

#     Parameters:
#         file_path (str): Path to the input TSV file.

#     Returns:
#         pd.DataFrame: Modified DataFrame with deduplicated ANN[*].EFFECT column and one effect per row.

#     Note:

#     """
#     try:
#         # Read the TSV file into a DataFrame
#         df = pd.read_csv(file_path, delimiter="\t")
#         df = df.drop(["ANN[*].IMPACT"], axis=1, errors="ignore")
#         df.rename(
#             columns={"ANN[*].EFFECT": "EFFECT", "ANN[*].ALLELE": "ALT"},
#             errors="raise",
#             inplace=True,
#         )
#         # Deduplicate the values in the ANN[*].EFFECT column
#         # df["EFFECT"] = df["EFFECT"].str.split(",").apply(set).str.join(",")
#         # df['ANN[*].IMPACT'] = ''

#         # Split the records into one effect per row
#         # df = df.explode('ANN[*].EFFECT')
#         df.drop_duplicates(inplace=True)

#         # Reset the index
#         df = df.reset_index(drop=True)
#         # print(df)
#         return df
#     except KeyError as e:
#         LOGGER.error(e)
#         LOGGER.error(df.columns)
#         raise
#     except Exception as e:
#         LOGGER.error(e)
#         raise

# def read_sonar_hash(file_path: str):
#     with open(file_path, "r") as file:
#         data = json.load(file)
#     return data


# def export_vcf_SonarCMD(
#     db_path: str, refmol: str, sample_name: str, output_vcf: str
# ) -> None:
#     sonar_cmd = [
#         "sonar",
#         "match",
#         "--db",
#         db_path,
#         "-r",
#         refmol,
#         "--sample",
#         sample_name,
#         "--format",
#         "vcf",
#         "-o",
#         output_vcf,
#     ]
#     try:
#         subprocess.run(sonar_cmd, check=True)
#         # print("Sonar command executed successfully.")
#     except subprocess.CalledProcessError as e:
#         print("Sonar match command failed:", e)


# def import_annvcf_SonarCMD(db_path, sonar_hash, ann_input):
#     sonar_cmd = [
#         "sonar",
#         "import-ann",
#         "--db",
#         db_path,
#         "--sonar-hash",
#         sonar_hash,
#         "--ann-input",
#         ann_input,
#     ]
#     try:
#         subprocess.run(sonar_cmd, check=True)

#         # print("Sonar command executed successfully.")
#     except subprocess.CalledProcessError as e:
#         print("Sonar import-ann command failed:", e)
