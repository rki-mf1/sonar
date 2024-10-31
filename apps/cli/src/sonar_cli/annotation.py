import os
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
                LOGGER.error(
                    "SnpEff annotation failed with exit code: %s", result.returncode
                )
                LOGGER.error("Command to reproduce the error: %s", command)

                with open(self.sonar_cache.error_logfile_name, "a+") as writer:
                    writer.write("Fail anno:" + command + "\n")

                LOGGER.error(result.stderr.decode("utf-8").splitlines())
                # in case the file is corrupted during annotation
                if os.path.exists(output_vcf):
                    os.remove(output_vcf)
                # Raise an exception to stop the worker
                raise RuntimeError("SnpEff annotation failed")

        except subprocess.CalledProcessError as e:
            LOGGER.error("SnpEff annotation failed: %s", e)
            # in case the file is corrupted during annotation
            if os.path.exists(output_vcf):
                os.remove(output_vcf)
            with open(self.sonar_cache.error_logfile_name, "a+") as writer:
                writer.write("Annotation failed:" + e + "\n")
            raise  # Raise exception to stop the process

    def bcftools_filter(self, input_vcf, output_vcf):
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
