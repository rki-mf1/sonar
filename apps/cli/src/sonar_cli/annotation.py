import os
from pathlib import Path
import shutil
import subprocess
from typing import Optional

from sonar_cli.cache import sonarCache
from sonar_cli.logging import LoggingConfigurator

# Initialize logger
LOGGER = LoggingConfigurator.get_logger()


class Annotator:
    def __init__(
        self,
        annotator_exe_path=None,
        VCF_ONEPERLINE_PATH=None,
        config_path=None,
        cache: Optional[sonarCache] = None,
    ) -> None:
        # "snpEff/SnpSift.jar"
        self.annotator = annotator_exe_path
        self.VCF_ONEPERLINE_TOOL = VCF_ONEPERLINE_PATH
        self.config_path = config_path
        self.sonar_cache = cache

    def snpeff_annotate(self, input_vcf, output_vcf, database_name):
        if not self.annotator:
            raise ValueError("Annotator executable path is not provided.")
        # Command to annotate using SnpEff
        command = [
            f"{self.annotator}",
            "eff",
            f"{database_name}",
            f"{input_vcf}",
            "-noStats",
            "-noLof",
        ]
        # custom dataDIR
        command.extend(["-nodownload", "-dataDir", self.sonar_cache.snpeff_data_dir])

        if self.config_path:
            command.extend(
                ["-nodownload", "-config", Path(f"{self.config_path}").expanduser()]
            )

        try:
            # Run the SnpEff annotation
            with open(output_vcf, "w") as output_file:
                result = subprocess.run(
                    command,
                    stdout=output_file,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                )
            if result.returncode != 0:
                LOGGER.error(
                    f"SnpEff annotation failed with exit code: {result.returncode}"
                )
                LOGGER.error(f"Command to reproduce the error: {' '.join(command)}")
                with open(self.sonar_cache.error_logfile_name, "a+") as writer:
                    writer.write(f"Fail anno: {' '.join(command)}\n")
                LOGGER.error(result.stderr.decode("utf-8").splitlines())
                # in case the file is corrupted during annotation
                if os.path.exists(output_vcf):
                    os.remove(output_vcf)
                # Raise an exception to stop the worker
                raise RuntimeError("SnpEff annotation failed")

        except subprocess.CalledProcessError as e:
            LOGGER.error(f"SnpEff annotation failed: {e}")
            # in case the file is corrupted during annotation
            if os.path.exists(output_vcf):
                os.remove(output_vcf)
            with open(self.sonar_cache.error_logfile_name, "a+") as writer:
                writer.write(f"Annotation failed: {e}\n")
            raise

    def bcftools_filter(self, input_vcf, output_vcf):
        """Only retain variants with ANN="""

        # The bcftools view command will fail if the input vcf has zero
        # variants, so we check for this explicity and just return the input
        # vcf if that is the case
        stats_command = f"bcftools stats {input_vcf}"
        stats_process = subprocess.run(
            stats_command, shell=True, stdout=subprocess.PIPE
        )
        stat_text = stats_process.stdout
        for line in stat_text.decode("utf-8").splitlines():
            fields = line.split("\t")
            if (
                fields[0] == "SN"
                and fields[1] == "0"
                and fields[2] == "number of records:"
                and fields[3] == "0"
            ):
                # the vcf contains zero records (SNPs + indels). Do not filter.
                shutil.copyfile(input_vcf, output_vcf)
                return

        # The vcf has at least one record, so the view command should not fail
        filter_command = f"bcftools view -e 'INFO/ANN=\".\"' {input_vcf} > {output_vcf}"

        # Execute the filter command
        filter_process = subprocess.run(
            filter_command, shell=True, stderr=subprocess.PIPE
        )
        if filter_process.returncode != 0:
            # in case the file is corrupted during bcftool
            if os.path.exists(output_vcf):
                os.remove(output_vcf)

            LOGGER.error("Error occurred while filtering the VCF file.")
            error_message = filter_process.stderr.decode("utf-8").strip()
            LOGGER.error(f"Error message: {error_message}")
            with open(self.sonar_cache.error_logfile_name, "a+") as writer:
                writer.write("Fail bcftools_filter:" + filter_command + "\n")
            raise RuntimeError(
                f"bcftools filter failed with exit code {filter_process.returncode}"
            )

    # def bcftools_split(
    #     self, input_vcf, output_vcfs=[], map_name_annovcf_dict: dict = {}
    # ):
    #     filtered_vcf = f"{input_vcf}.filtered"
    #     # Define the command to filter the VCF file
    #     filter_command = (
    #         f"bcftools view -e 'INFO/ANN=\".\"' {input_vcf} > {filtered_vcf}"
    #     )

    #     # Execute the filter command
    #     filter_process = subprocess.run(filter_command, shell=True)
    #     if filter_process.returncode != 0:
    #         LOGGER.error("Error occurred while filtering the VCF file.")
    #         with open(self.sonar_cache.error_logfile_name, "a+") as writer:
    #             writer.write("Fail bcftools_split:" + filter_command + "\n")
    #     # Get the list of sample names from the command output
    #     sample_names_cmd = f"bcftools query -l {filtered_vcf}"
    #     sample_names_process = subprocess.run(
    #         sample_names_cmd, shell=True, capture_output=True, text=True
    #     )

    #     if sample_names_process.returncode != 0:
    #         LOGGER.error("Error occurred while getting sample names.")
    #         LOGGER.error("Error output:", sample_names_process)
    #         exit()

    #     sample_names = sample_names_process.stdout.strip().split()

    #     # Process each sample
    #     for sample in sample_names:
    #         anno_vcf = map_name_annovcf_dict[sample]
    #         # --no-header suppress the header in VCF output
    #         cmd = f"bcftools view --exclude-uncalled --no-header --trim-alt-alleles -s {sample} {filtered_vcf} -Oz -o {anno_vcf}"
    #         process = subprocess.run(cmd, shell=True)

    #         if process.returncode != 0:
    #             LOGGER.error(f"Error occurred while processing sample {sample}")
    #             with open(self.sonar_cache.error_logfile_name, "a+") as writer:
    #                 writer.write("Fail bcftools_split:" + cmd + "\n")

    #     if os.path.exists(filtered_vcf):
    #         os.remove(filtered_vcf)

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
            if result.returncode != 0:
                LOGGER.error("bgzip failed for VCF %s", vcf_path)
                # Decode and log the error message
                error_message = result.stderr.decode("utf-8").strip()
                LOGGER.error(f"Error message: {error_message}")
                raise RuntimeError(
                    f"bgzip failed for VCF {vcf_path} with exit code {result.returncode}"
                )

            # Execute tabix command
            result = subprocess.run(tabix_cmd, shell=True, stderr=subprocess.PIPE)
            if result.returncode != 0:
                LOGGER.error("tabix indexing failed for VCF %s", compressed_vcf)
                error_message = result.stderr.decode("utf-8").strip()
                LOGGER.error(f"Error message: {error_message}")
                raise RuntimeError(
                    f"tabix indexing failed for VCF {compressed_vcf} with exit code {result.returncode}"
                )

        # Merge.
        # bcftools = can use --use-header to modify VCF header or reheader command
        full_inputs = " ".join(compressed_vcf_list)
        command = f"bcftools merge {full_inputs} -o {output_vcf}  "
        result = subprocess.run(command, shell=True, stderr=subprocess.PIPE)

        if result.returncode != 0:
            # in case the file is corrupted during bcftool
            if os.path.exists(output_vcf):
                os.remove(output_vcf)

            LOGGER.error("bcftools merge failed with exit code: %s", result.returncode)
            LOGGER.error(result.stderr.decode("utf-8"))
            LOGGER.error("Input file: %s", input_vcfs)
            LOGGER.error("Output file: %s", output_vcf)
            error_message = result.stderr.decode("utf-8").strip()
            LOGGER.error(f"Error message: {error_message}")
            with open(self.sonar_cache.error_logfile_name, "a+") as writer:
                writer.write("Fail bcftools_merge:" + error_message + "\n")
                writer.write(command + "\n")
            raise RuntimeError(
                f"bcftools merge failed with exit code {result.returncode}"
            )
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
    #             LOGGER.error("Error output:", result.stderr.decode("utf-8"))
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
#
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
#         # LOGGER.info("Sonar command executed successfully.")
#     except subprocess.CalledProcessError as e:
#         LOGGER.error("Sonar match command failed:", e)


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

#         # LOGGER.info("Sonar command executed successfully.")
#     except subprocess.CalledProcessError as e:
#         LOGGER.error("Sonar import-ann command failed:", e)
